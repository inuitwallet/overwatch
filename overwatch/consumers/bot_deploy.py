import json
import os
import shutil
import subprocess
from tempfile import mkdtemp
from venv import create

import boto3
from botocore.config import Config
from channels.consumer import SyncConsumer
from django.conf import settings

from overwatch.models import Bot


class BotDeployConsumer(SyncConsumer):
    def get_function_names(self, client, function_names=None, next_marker=None):
        if function_names is None:
            function_names = []

        if next_marker is not None:
            response = client.list_functions(Marker=next_marker, MaxItems=50)
        else:
            response = client.list_functions(MaxItems=50)

        for func in response.get('Functions', []):
            function_names.append(func.get('FunctionName'))

        if 'NextMarker' in response:
            return self.get_function_names(function_names, response['NextMarker'])

        return function_names

    def deploy(self, event):
        bot_pk = event.get('bot_pk')

        try:
            bot = Bot.objects.get(pk=bot_pk)
        except Bot.DoesNotExist:
            print('Could not find a Bot with pk {}'.format(bot_pk))
            return

        print('Deploying bot {}'.format(bot))

        # Ensure the bot has the fields needed
        missing_fields = False

        for field in ['name', 'exchange', 'bot_type', 'aws_access_key', 'aws_secret_key', 'exchange_api_key',
                      'exchange_api_secret', 'base_url', 'schedule', 'aws_region']:
            if not getattr(bot, field):
                print('Bot does not have a valid {} field'.format(field))
                missing_fields = True

        if missing_fields:
            print('Aborting deploy due to missing fields')
            return

        # we should move the chosen bot code to a temp directory ready for building
        working_dir = mkdtemp()
        print('Working in {}'.format(working_dir))
        shutil.copytree(
            os.path.join(settings.BASE_DIR, 'overwatch', 'bots', bot.bot_type),
            os.path.join(working_dir, 'bot')
        )
        print('Creating virtualenv')
        create('{}/ve'.format(os.path.join(working_dir, 'bot')), with_pip=True)

        try:
            print('Installing dependencies')
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
            print('Error installing requirements: {}'.format(e))
            shutil.rmtree(working_dir)
            return

        return

        print('Creating Zappa settings file')
        project_name = 'overwatch_bot_{}_{}'.format(bot.exchange, bot.name)
        json.dump(
            {
                'prod': {
                    'app_function': 'bot.main',
                    'aws_region': '{}'.format(bot.aws_region),
                    'profile_name': 'default',
                    'project_name': project_name,
                    'runtime': 'python3.6',
                    's3_bucket': 'overwatch_bot'
                }
            },
            open('{}/zappa_settings.json'.format(os.path.join(working_dir, 'bot')), 'w+')
        )

        print('Zipping Archive with Zappa')

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
            print('Error Zipping with Zappa: {}'.format(e))
            shutil.rmtree(working_dir)
            return

        print('Uploading {}.zip archive to Lambda'.format(project_name))

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

        if project_name in self.get_function_names(client):
            # function already exists
            function_exists = True

        with open(
            '{}.zip'.format(os.path.join(working_dir, project_name)),
            'rb'
        ) as function_zip:
            try:
                if function_exists:
                    response = client.update_function_code(
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
                    iam_client.attach_role_policy(
                        RoleName=project_name,
                        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    )
                    response = client.create_function(
                        FunctionName=project_name,
                        Runtime='python3.6',
                        Role=role_response['Role']['Arn'],
                        Handler='bot.main',
                        Code={'ZipFile': function_zip.read()},
                    )
                print('Upload Successful')
            except Exception as e:
                print('Failed to upload: {}'.format(e))
                shutil.rmtree(working_dir)
                return

            print('Updating {} config'.format(project_name))
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
                    Runtime='python3.6'
                )
                print('Config Updated Successfully')
            except Exception as e:
                print('Failed to update config: {}'.format(e))
                shutil.rmtree(working_dir)
                return

            # we can create a CloudWatch Event and enable it
            print('Updating Schedule')
            event_client = boto3.client(
                'events',
                config=Config(connect_timeout=120, read_timeout=120),
                aws_access_key_id=bot.aws_access_key,
                aws_secret_access_key=bot.aws_secret_key,
                region_name=bot.aws_region
            )

            rule_response = self.update_cloudwatch_event(bot, event_client)

            try:
                client.add_permission(
                    FunctionName=project_name,
                    StatementId="{}-Event".format(project_name),
                    Action='lambda:InvokeFunction',
                    Principal='events.amazonaws.com',
                    SourceArn=rule_response['RuleArn'],
                )
            except Exception:
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

        # clean up the working directory
        shutil.rmtree(working_dir)

        # set the cloudwatch logs group
        bot.logs_group = '/aws/lambda/overwatch_bot_{}_{}'.format(bot.exchange, bot.name)
        bot.save()

        print('Deployment of bot {} is complete'.format(bot))

    def deactivate(self, event):
        bot_pk = event.get('bot_pk')

        try:
            bot = Bot.objects.get(pk=bot_pk)
        except Bot.DoesNotExist:
            print('Could not find a Bot with pk {}'.format(bot_pk))
            return

        print('Deactivating bot {}'.format(bot))
        self.update_cloudwatch_event(bot)

    def activate(self, event):
        bot_pk = event.get('bot_pk')

        try:
            bot = Bot.objects.get(pk=bot_pk)
        except Bot.DoesNotExist:
            print('Could not find a Bot with pk {}'.format(bot_pk))
            return

        print('Deactivating bot {}'.format(bot))
        self.update_cloudwatch_event(bot)

    @staticmethod
    def update_cloudwatch_event(bot, event_client=None):
        project_name = 'overwatch_bot_{}_{}'.format(bot.exchange, bot.name)

        if event_client is None:
            event_client = boto3.client(
                'events',
                config=Config(connect_timeout=120, read_timeout=120),
                aws_access_key_id=bot.aws_access_key,
                aws_secret_access_key=bot.aws_secret_key,
                region_name=bot.aws_region
            )

        try:
            print('ENABLED' if bot.active else 'DISABLED')
            change_rule = event_client.put_rule(
                Name=project_name,
                ScheduleExpression='rate({} minutes)'.format(bot.schedule),
                State='ENABLED' if bot.active else 'DISABLED',
                Description='Event timer for {}'.format(project_name),
            )
            print(change_rule)
            return change_rule
        except Exception as e:
            print('Failed to update Cloudwatch Event: {}'.format(e))
            return False
