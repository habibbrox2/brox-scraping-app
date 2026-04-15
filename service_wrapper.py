"""
Windows Service Wrapper for ScrapMaster
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess
import signal
import threading
import time

class ScrapMasterService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ScrapMasterService"
    _svc_display_name_ = "ScrapMaster Desktop Service"
    _svc_description_ = "Background service for ScrapMaster web scraping application"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process = None
        self.running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)

        # Stop the subprocess
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                            servicemanager.PYS_SERVICE_STARTED,
                            (self._svc_name_, ''))

        # Change to application directory
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(app_dir)

        # Start the main application in background mode
        try:
            self.process = subprocess.Popen(
                [sys.executable, 'main.py', '--service'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Monitor the process
            while self.running:
                ret = win32event.WaitForSingleObject(self.hWaitStop, 1000)
                if ret == win32event.WAIT_OBJECT_0:
                    break

                # Check if process is still running
                if self.process.poll() is not None:
                    # Process exited, restart it
                    servicemanager.LogErrorMsg("ScrapMaster process exited, restarting...")
                    self.process = subprocess.Popen(
                        [sys.executable, 'main.py', '--service'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )

        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {e}")

        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                            servicemanager.PYS_SERVICE_STOPPED,
                            (self._svc_name_, ''))

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ScrapMasterService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ScrapMasterService)