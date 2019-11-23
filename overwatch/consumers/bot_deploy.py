import json
import logging
import os
import shutil
import subprocess
import time
from tempfile import mkdtemp
from venv import create

import boto3
from asgiref.sync import async_to_sync
from botocore.config import Config
from channels.consumer import SyncConsumer
from channels.layers import get_channel_layer
from django.conf import settings

from overwatch.models import Bot

logger = logging.getLogger(__name__)


class BotDeployConsumer(SyncConsumer):
    @staticmethod
    def _notify_ui(bot_pk, message, target):
        logger.info(message)
        async_to_sync(get_channel_layer().group_send)(
            'bot_{}'.format(bot_pk),
            {
                'type': 'send.ui.notification',
                'target': target,
                'text': message
            }
        )

    def _get_function_names(self, client, function_names=None, next_marker=None):
        if function_names is None:
            function_names = []

        if next_marker is not None:
            response = client.list_functions(Marker=next_marker, MaxItems=50)
        else:
            response = client.list_functions(MaxItems=50)

        for func in response.get('Functions', []):
            function_names.append(func.get('FunctionName'))

        if 'NextMarker' in response:
            return self._get_function_names(function_names, response['NextMarker'])

        return function_names

    def _update_config(self, bot, project_name, client, target):
        self._notify_ui(bot.pk, 'Updating {} config'.format(project_name), target)
        try:
            config_response = client.update_function_configuration(
                FunctionName=project_name,
                Handler='bot.main',
                Timeout=bot.timeout,
                Environment={
                    "Variables": {
                        "API_KEY": bot.exchange_api_key,
                        "API_SECRET": bot.exchange_api_secret,
                        "BASE_URL": bot.base_url,
                        "BOT_NAME": bot.name,
                        "EXCHANGE": bot.exchange.lower(),
                        "OVERWATCH_API_SECRET": '{}'.format(bot.api_secret),
                        "SLEEP_LONG": '{}'.format(bot.sleep_long),
                        "SLEEP_MEDIUM": '{}'.format(bot.sleep_medium),
                        "SLEEP_SHORT": '{}'.format(bot.sleep_short),
                        "VIGIL_FUNDS_ALERT_CHANNEL_ID": bot.vigil_funds_alert_channel_id,
                        "VIGIL_WRAPPER_ERROR_CHANNEL_ID": bot.vigil_wrapper_error_channel_id
                    }
                },
                Runtime='python3.7'
            )
            self._notify_ui(bot.pk, 'Config Updated Successfully', target)
        except Exception as e:
            self._notify_ui(bot.pk, 'Error: Failed to update config: {}'.format(e), target)
            return False

        # we can create a CloudWatch Event and enable it
        self._notify_ui(bot.pk, 'Updating Schedule', target)
        event_client = boto3.client(
            'events',
            config=Config(connect_timeout=120, read_timeout=120),
            aws_access_key_id=bot.aws_access_key,
            aws_secret_access_key=bot.aws_secret_key,
            region_name=bot.aws_region
        )

        rule_response = self._update_cloudwatch_event(bot, target, event_client)

        try:
            client.add_permission(
                FunctionName=project_name,
                StatementId="{}-Event".format(project_name),
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=rule_response['RuleArn'],
            )
        except Exception as e:
            pass

        target_ids = [
            target['Id'] for target in event_client.list_targets_by_rule(Rule=project_name).get('Targets', [])
        ]

        if len(target_ids) > 0:
            event_client.remove_targets(
                Rule=project_name,
                Ids=target_ids
            )

        event_client.put_targets(
            Rule=project_name,
            Targets=[
                {
                    'Id': "1",
                    'Arn': config_response['FunctionArn'],
                },
            ]
        )
        
        return True

    def _update_cloudwatch_event(self, bot, target, event_client=None):
        project_name = '{}overwatch_bot_{}_{}'.format(settings.BOT_PREFIX, bot.exchange, bot.name)

        if event_client is None:
            event_client = boto3.client(
                'events',
                config=Config(connect_timeout=120, read_timeout=120),
                aws_access_key_id=bot.aws_access_key,
                aws_secret_access_key=bot.aws_secret_key,
                region_name=bot.aws_region
            )

        try:
            return event_client.put_rule(
                Name=project_name,
                ScheduleExpression='rate({} minutes)'.format(bot.schedule),
                State='ENABLED' if bot.active else 'DISABLED',
                Description='Event timer for {}'.format(project_name),
            )
        except Exception as e:
            self._notify_ui(bot.pk, 'Error: Failed to update Cloudwatch Event: {}'.format(e), target)
            return False

    #####
    # Methods below here are callable from channels
    #####

    def update(self, event):
        bot_pk = event.get('bot_pk')

        try:
            bot = Bot.objects.get(pk=bot_pk)
        except Bot.DoesNotExist:
            self._notify_ui(bot_pk, 'Error: Could not find a Bot with pk {}'.format(bot_pk), 'update')
            return

        config = Config(connect_timeout=120, read_timeout=120)
        client = boto3.client(
            'lambda',
            config=config,
            aws_access_key_id=bot.aws_access_key,
            aws_secret_access_key=bot.aws_secret_key,
            region_name=bot.aws_region
        )

        project_name = '{}overwatch_bot_{}_{}'.format(settings.BOT_PREFIX, bot.exchange, bot.name)

        self._update_config(bot, project_name, client, 'update')

        self._notify_ui(bot_pk, 'Update Complete', 'update')

    def deactivate(self, event):
        bot_pk = event.get('bot_pk')

        try:
            bot = Bot.objects.get(pk=bot_pk)
        except Bot.DoesNotExist:
            self._notify_ui(bot_pk, 'Error: Could not find a Bot with pk {}'.format(bot_pk), 'deactivate')
            return

        self._notify_ui(bot_pk, 'Deactivating bot {}'.format(bot), 'deactivate')
        self._update_cloudwatch_event(bot)

    def activate(self, event):
        bot_pk = event.get('bot_pk')

        try:
            bot = Bot.objects.get(pk=bot_pk)
        except Bot.DoesNotExist:
            self._notify_ui(bot_pk, 'Error: Could not find a Bot with pk {}'.format(bot_pk), 'activate')
            return

        self._notify_ui(bot_pk, 'Activating bot {}'.format(bot), 'activate')
        self._update_cloudwatch_event(bot)

    def deploy(self, event):
        bot_pk = event.get('bot_pk')

        try:
            bot = Bot.objects.get(pk=bot_pk)
        except Bot.DoesNotExist:
            self._notify_ui(bot_pk, 'Error: Could not find a Bot with pk {}'.format(bot_pk), 'deploy')
            return

        self._notify_ui(bot_pk, 'Deploying Bot {}'.format(bot), 'deploy')

        # Ensure the bot has the fields needed
        missing_fields = False

        for field in ['name', 'exchange', 'bot_type', 'aws_access_key', 'aws_secret_key', 'exchange_api_key',
                      'exchange_api_secret', 'base_url', 'schedule', 'aws_region']:
            if not getattr(bot, field):
                self._notify_ui(bot_pk, 'Error: Bot does not have a valid {} field'.format(field), 'deploy')
                missing_fields = True

        if missing_fields:
            self._notify_ui(bot_pk, 'Error: Aborting deploy due to missing fields', 'deploy')
            return

        # we should move the chosen bot code to a temp directory ready for building
        working_dir = mkdtemp()
        self._notify_ui(bot_pk, 'Working in {}'.format(working_dir), 'deploy')
        shutil.copytree(
            os.path.join(settings.BASE_DIR, 'overwatch', 'bots', bot.bot_type),
            os.path.join(working_dir, 'bot')
        )
        self._notify_ui(bot_pk, 'Creating virtualenv', 'deploy')
        create('{}/ve'.format(os.path.join(working_dir, 'bot')), with_pip=True)

        try:
            self._notify_ui(bot_pk, 'Installing dependencies', 'deploy')
            subprocess.run(
                [
                    've/bin/pip',
                    'install',
                    '-r'
                    'requirements.txt',
                    '--upgrade'
                ],
                cwd=os.path.join(working_dir, 'bot')
            )
            # install zappa
            subprocess.run(
                [
                    've/bin/pip',
                    'install',
                    'zappa',
                    '--upgrade'
                ],
                cwd=os.path.join(working_dir, 'bot')
            )

        except Exception as e:
            self._notify_ui(bot_pk, 'Error: Error installing requirements: {}'.format(e), 'deploy')
            shutil.rmtree(working_dir)
            return

        self._notify_ui(bot_pk, 'Creating Zappa settings file', 'deploy')
        project_name = '{}overwatch_bot_{}_{}'.format(settings.BOT_PREFIX, bot.exchange, bot.name)
        json.dump(
            {
                'prod': {
                    'app_function': 'bot.main',
                    'aws_region': '{}'.format(bot.aws_region),
                    'profile_name': 'default',
                    'project_name': project_name,
                    'runtime': 'python3.7',
                    's3_bucket': 'overwatch_bot'
                }
            },
            open('{}/zappa_settings.json'.format(os.path.join(working_dir, 'bot')), 'w+')
        )

        self._notify_ui(bot_pk, 'Zipping Archive with Zappa', 'deploy')

        # create the zappa bash file to handle activating the project virtualenv
        with open('{}/zappa_package.sh'.format(os.path.join(working_dir, 'bot')), 'w+') as zappa_bash:
            zappa_bash.write('#!/bin/bash\n\n')
            zappa_bash.write('. ve/bin/activate\n')
            zappa_bash.write('zappa package prod -o {}.zip'.format(
                os.path.join(working_dir, project_name)
            ))

        try:
            subprocess.run(
                [
                    '/bin/bash',
                    'zappa_package.sh'
                ],
                cwd=os.path.join(working_dir, 'bot')
            )

        except Exception as e:
            self._notify_ui(bot_pk, 'Error: Error Zipping with Zappa: {}'.format(e), 'deploy')
            shutil.rmtree(working_dir)
            return

        self._notify_ui(bot_pk, 'Uploading {}.zip archive to Lambda'.format(project_name), 'deploy')

        config = Config(connect_timeout=120, read_timeout=120)
        client = boto3.client(
            'lambda',
            config=config,
            aws_access_key_id=bot.aws_access_key,
            aws_secret_access_key=bot.aws_secret_key,
            region_name=bot.aws_region
        )

        # se if the named function already exists
        function_exists = False

        if project_name in self._get_function_names(client):
            # function already exists
            function_exists = True

        with open(
                '{}.zip'.format(os.path.join(working_dir, project_name)),
                'rb'
        ) as function_zip:
            try:
                if function_exists:
                    client.update_function_code(
                        FunctionName=project_name,
                        ZipFile=function_zip.read(),
                        Publish=True
                    )
                else:
                    # need the ARN of a service Role
                    iam_client = boto3.client(
                        'iam',
                        config=config,
                        aws_access_key_id=bot.aws_access_key,
                        aws_secret_access_key=bot.aws_secret_key,
                        region_name=bot.aws_region
                    )

                    # first check if the role already exists
                    check_role_response = iam_client.list_roles(
                        PathPrefix='/service-role/',
                    )

                    role_arn = None

                    for role in check_role_response.get('Roles', []):
                        if role.get('RoleName') == project_name:
                            role_arn = role.get('Arn')
                            print(role)

                    if not role_arn:
                        role_response = iam_client.create_role(
                            Path='/service-role/',
                            RoleName=project_name,
                            AssumeRolePolicyDocument=json.dumps(
                                {
                                    "Version": "2012-10-17",
                                    "Statement": [
                                        {
                                            "Sid": "",
                                            "Effect": "Allow",
                                            "Principal": {
                                                "Service": "lambda.amazonaws.com"
                                            },
                                            "Action": "sts:AssumeRole"
                                        }
                                    ]
                                }
                            ),
                            Description='Lambda execution role for {}'.format(project_name)
                        )
                        role_arn = role_response['Role']['Arn']
                        # sleep to allow the role to become active
                        time.sleep(30)

                    iam_client.attach_role_policy(
                        RoleName=project_name,
                        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    )

                    client.create_function(
                        FunctionName=project_name,
                        Runtime='python3.7',
                        Role=role_arn,
                        Handler='bot.main',
                        Code={'ZipFile': function_zip.read()},
                    )
                self._notify_ui(bot_pk, 'Upload Successful', 'deploy')
            except Exception as e:
                self._notify_ui(bot_pk, 'Error: Failed to upload: {}'.format(e), 'deploy')
                shutil.rmtree(working_dir)
                return

        # update the config
        self._update_config(bot, project_name, client, 'deploy')

        # clean up the working directory
        shutil.rmtree(working_dir)

        # set the cloudwatch logs group
        bot.logs_group = '/aws/lambda/{}'.format(project_name)
        bot.save()

        self._notify_ui(bot_pk, 'Deployment of bot {} is complete'.format(bot), 'deploy')
