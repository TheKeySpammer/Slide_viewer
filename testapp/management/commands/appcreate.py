# from django.core.management.base import BaseCommand, CommandError
# from testapp.models import TestApp
# from django.core import management
# import subprocess
# from subprocess import Popen, PIPE
# import time

# class Command(BaseCommand):
#     help = 'Closes the specified poll for voting'

#     def handle(self, *args, **options):

        # proc = subprocess.Popen(
        #     ['python', 'manage.py', 'migrate'],
        #     stdout=subprocess.DEVNULL,  # if you skip these lines
        #     stderr=subprocess.DEVNULL,  # you must call `proc.communicate()`
        # )

        # # # wait for the process to finish
        # proc.wait()
        # proc.terminate()
        # proc.kill()
        # management.call_command('migrate')
        # subprocess.call(["/home/bilal/Desktop/Bilal/virtualcases/env/bin/python", "manage.py", "migrate"])
        # return TestApp.testing_func('Bilal')

        # proc = subprocess.Popen(['python', 'manage.py', 'migrate'],
        #                     stdout=subprocess.PIPE,
        #                     stderr=subprocess.STDOUT)

        # try:
        #     time.sleep(0.1)
        # finally:
        #     proc.terminate()
        #     proc.kill()
        #     try:
        #         outs, _ = proc.communicate(timeout=0.1)
        #         print('== subprocess exited with rc =', proc.returncode)
        #         print(outs.decode('utf-8'))
        #     except subprocess.TimeoutExpired:
        #         print('subprocess did not terminate in time')

        # import subprocess, os
        # my_env = os.environ.copy()
        # my_env["PATH"] = "/usr/sbin:/sbin:" + my_env["PATH"]
        # subprocess.Popen(["python", "manage.py", "migrate"], env=my_env)
        # subprocess.Popen(["/home/bilal/Desktop/Bilal/virtualcases/env/bin/python", "manage.py", "migrate"])

        
        
        # try:
        #     proc = subprocess.Popen(["/home/bilal/Desktop/Bilal/virtualcases/env/bin/python", "manage.py", "migrate"])
        # finally:
        #     proc.terminate()