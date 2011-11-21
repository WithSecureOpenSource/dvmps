from PySide.QtCore import Qt, QObject, Slot, QFile
from PySide.QtGui import QApplication, QTreeWidgetItem, QMessageBox
from PySide.QtUiTools import QUiLoader
#from PySide import QtXml
import random
import time
from threading import Thread, Event
import Queue, getpass
from kvm import (allocateMachine, deallocate, listRunningVms, listTemplates,
                connectWithRemoteDesktop, canConnectWithRemoteDesktop, Curry)
from progress_dialog import ProgressDialog
"""
TODO:    
    code cleanup:
    de-hardcode
    may be worth removing 'workers' from here and move to kvm.py to reduce
    code fragmentation
    
    power on:
    implement

    power off:
    implement

    info about a running vm:
    implement
    
    on deallocate do progress popup
    
    right button popup menu on deployed vm's lists

    preserve sort order in deployed vms list
    
    implement proper sorting for the fields (case insensitive, ip add and so)
"""

HOSTS = {'TA blade 01': '10.133.34.2',
         'TA blade 02': '10.133.34.3',
         'TA blade 03': '10.133.34.4',
         'TA blade 04': '10.133.34.5',
         'TA blade 05': '10.133.34.6'}

def secondsToHMS(seconds):
    '''Converts the given seconds into HH:MM:SS format'''
    hours = seconds / 3600
    seconds -= 3600*hours
    minutes = seconds / 60
    seconds -= 60*minutes
    return "%02d:%02d:%02d" % (hours, minutes, seconds)

def listTemplatesWorker(host, ret_queue):
    '''Returns the list of available templates in the given host'''
    ret = listTemplates(host)
    ret_queue.put(ret)
    
def deployWorker(template, expires, comment, host, ret_queue):
    '''Allocates a new VM from the given template.
    On success it puts the ip address of the newly allocated machine
    in ret_queue or None followed by an error message
    '''
    (result, ip_address, err_msg) = allocateMachine(host,
                                                    template,
                                                    expires,
                                                    comment)
    if result == False:
        ret_queue.put(None)
        ret_queue.put(err_msg)
    else:        
        ret_queue.put(ip_address)
        
def connectWorker(ip_address, progress_msgs, ret_queue, abort_event):
    '''Tries to connect with remote desktop to the given ip_addess, progress
    and retries are reported thru the queue 'progress_msgs'.
    When abort_event is set the connection attempt is aborted.
    Returns True in the queue ret_queue or False and the error message as the
    next element in ret_queue
    '''
    #returns True in ret_queue or false and then an error message
    reachable = False
    for i in range(30):
        progress_msgs.put("Attempting to reach %s (%i)" % (ip_address, i))
        if canConnectWithRemoteDesktop(ip_address):
            reachable = True
            break
        else:
            if abort_event.isSet():
                ret_queue.put(False)
                ret_queue.put("User cancelled...")
                return
        time.sleep(1)

    if not reachable:
        progress_msgs.put("Machine not reachable at %s" % ip_address)
        ret_queue.put(False)
        ret_queue.put("Machine not reachable at %s" % ip_address)
    else:
        progress_msgs.put("Launching remote desktop connection")
        connectWithRemoteDesktop(ip_address)
        ret_queue.put(True)

def listRunningVMWorker(host, progress_msgs, running_vms):
    '''Fetches the list of virtual machines running in 'host' and puts the
    result in the queue 'running_vms', reports it's progress in the queue
    'progress_msgs'
    '''
    progress_msgs.put("Fetching list from host %s" % host)
    response = listRunningVms(host)
    for image in response['running_images']:
        lst = []
        lst.append(image['ip_addr'])
        lst.append(image['comment'])
        lst.append(secondsToHMS(image['valid_for']))
        lst.append(image['base_image'])
        lst.append(image['image_id'])
        lst.append(host)
        running_vms.put(lst)

    running_vms.put(None)
    
def resolveHost(host):
    '''Resolves the name of the host into it's ip address or a random one'''
    if not host in HOSTS:
        return HOSTS.values()[random.randint(0, len(HOSTS)-1)]
    else:
        return HOSTS[host]        

def loadWindowFromFile(file_name):
    '''Load the window definition from the resource ui file'''
    loader = QUiLoader()
    ui_file = QFile(file_name)
    ui_file.open(QFile.ReadOnly)
    the_window = loader.load(ui_file)
    ui_file.close()
    return the_window

def isAlive(threads):
    '''Returns True if at least one thread in the given list of threads is
    still running (alive)
    '''
    still_running = False
    for a_thread in threads:
        if a_thread.isAlive() == True:
            still_running = True
            break
    return still_running

class KvmUI(QObject):
    ''' UI Wrapper to kvm operations'''
    
    def __init__(self):
        QObject.__init__(self)
        self._mywindow = loadWindowFromFile(r'mainwindow.ui')
        self._mywindow.le_expires.setText("90")
        self._width_of_vm_frame = 400
        self._connectWidgetSignals()
        self._progress_dlg = ProgressDialog()

    def _connectWidgetSignals(self):
        '''Connect all the widget events with the appropriate slots'''
        self._mywindow.bt_refresh_templates.clicked.connect(
            self.loadTemplatesList)
        self._mywindow.bt_deploy.clicked.connect(self.deploySelectedTemplates)
        self._mywindow.bt_deploy_and_connect.clicked.connect(
            Curry(self.deploySelectedTemplates, True))
        self._mywindow.bt_reconnect.clicked.connect(
            self.connectToSelected)
        self._mywindow.bt_refresh_running_vms.clicked.connect(
            self.loadRunningVmsFromSelectedHost)
        self._mywindow.bt_show_running_vms.clicked.connect(
            self.showHideRunningVms)
        self._mywindow.bt_connect.clicked.connect(
            self.connectToSelectedFromRunning)
        self._mywindow.bt_deallocate.clicked.connect(
            self.deallocateSelected)
        self._mywindow.tw_deployed.itemDoubleClicked.connect(
            self.connectToSelected)
        self._mywindow.lv_templates.itemDoubleClicked.connect(
            Curry(self.deploySelectedFromDblClick,True))
        self._mywindow.tw_running_vms.itemDoubleClicked.connect(
            self.connectToSelectedFromRunning)
    
    def show(self):
        '''Shows the main ui'''
        self._mywindow.show()

    def setComment(self, comment):
        '''Sets the comment used when creating a vm'''
        self._mywindow.le_comment.setText(comment)
    
    @Slot()
    def showHideRunningVms(self):
        '''Shows / hides the running vm list'''
        if self._mywindow.gp_running_vm.isVisible():
            self._width_of_vm_frame = self._mywindow.gp_running_vm.width() + 5
            self._mywindow.gp_running_vm.hide()
            max_width = self._mywindow.maximumWidth()
            self._mywindow.setFixedWidth(
                self._mywindow.width() - self._width_of_vm_frame)
            self._mywindow.setMaximumWidth(max_width)
            self._mywindow.bt_show_running_vms.setText("Show Running vm's")
        else:
            self._mywindow.gp_running_vm.show()
            self._mywindow.resize(
                self._mywindow.width() + self._width_of_vm_frame,
                self._mywindow.height())
            self._mywindow.bt_show_running_vms.setText("Hide Running vm's")

    @Slot()
    def loadRunningVmsFromSelectedHost(self):
        '''Loads the running vm list from the hosts selected in the combobox'''
        if self._mywindow.cb_blades.currentText() == "Random":
            hostlist = HOSTS
        else:
            hostlist = {self._mywindow.cb_blades.currentText():
                        HOSTS[self._mywindow.cb_blades.currentText()]}
        self.loadRunningVms(hostlist)
        
    def loadRunningVms(self, hosts):
        '''Loads the running vm list from the given hosts'''
        self._progress_dlg.reportProgress("Fetching running vm's list...")
        self._progress_dlg.show(cancellable=False)
        progress_msgs = Queue.Queue()
        running_vms = Queue.Queue()
        workers = []
        for host in hosts.values():
            work = Thread(target=listRunningVMWorker, args=(host,
                                                            progress_msgs,
                                                            running_vms,))
            work.start()
            workers.append(work)
        
        self._waitForTask(workers,
                          progress_msgs=progress_msgs,
                          abort_event=None)
            
        self._mywindow.tw_running_vms.clear()
        end_marks = 0
        while end_marks != len(workers):
            elem = running_vms.get()
            if not elem is None:
                self._addRunningVmToList(elem)
            else:
                end_marks += 1
            
        self._mywindow.tw_running_vms.sortByColumn(0,
                                                  Qt.SortOrder.AscendingOrder)
        self._progress_dlg.close()
        
    @Slot()
    def _addRunningVmToList(self, lst):
        '''adds a vm to the running vm list from a list of strings'''
        #FIXME: use a dict
        itm = QTreeWidgetItem()
        itm.setText(0, lst[0])
        itm.setText(1, lst[1])
        itm.setText(2, lst[2])
        itm.setText(3, lst[3])
        itm.setText(4, lst[4])
        itm.setText(5, lst[5])
        self._mywindow.tw_running_vms.addTopLevelItem(itm)

    @Slot()
    def deploySelectedFromDblClick(self, connect_after=False, item=None):
        '''Deploys machines using the selected template, invoked by
        double-click
        '''
        self.deploySelectedTemplates(connect_after)
        
    @Slot()
    def deploySelectedTemplates(self, connect_after=False):
        '''Deploys machines using the selected templates'''
        templates = []
        for item in self._mywindow.lv_templates.selectedItems():
            templates.append(item.text())
        
        if len(templates) == 0:
            QMessageBox.warning(self._mywindow, "Template",
                                "Please select a template to deploy")
            return

        comment = self._mywindow.le_comment.text()
        expires = int(self._mywindow.le_expires.text())
        host = resolveHost(self._mywindow.cb_blades.currentText())
        
        self.deployTemplates(templates, comment, expires, host, connect_after)
        
    def deployTemplates(self, templates, comment, expires, host, connect_after):
        '''Deploys the provided templates as new vms'''
        for template in templates:
            self._progress_dlg.reportProgress("Deploying template...")
            self._progress_dlg.show(cancellable=False)
            ret_queue = Queue.Queue()
            work = Thread(target=deployWorker, args=(template,
                                                     expires,
                                                     comment,
                                                     host,
                                                     ret_queue,))
            work.start()
            self._waitForTask(work)
            self._progress_dlg.close()
            returned_ip = ret_queue.get()
            if returned_ip != None:
                self._addMachineToDeployedList(returned_ip, comment, host)
                if connect_after:
                    self.connect(returned_ip)
            else:
                err_msg = ret_queue.get()
                QMessageBox.warning(self._mywindow, "Error occurred",
                                    "Error: %s" % err_msg)

    def connect(self, ip_address):
        '''Connects to the given address using remote desktop, the method
        will check first if it can connect and retry if it cant
        '''
        self._progress_dlg.reportProgress("Connecting to %s..." % ip_address)
        self._progress_dlg.show(cancellable=True)
        progress_msgs = Queue.Queue()
        ret_queue = Queue.Queue()
        abort = Event()
        work = Thread(target=connectWorker, args=(ip_address, 
                                                  progress_msgs,
                                                  ret_queue, 
                                                  abort,))
        work.start()
        self._waitForTask(work, progress_msgs=progress_msgs,
                          abort_event=abort)
            
        returned = ret_queue.get()

        self._progress_dlg.close()
        if returned != True:
            err_msg = ret_queue.get()
            if not abort.isSet():
                self._progress_dlg.reportProgress(err_msg)
                self._progress_dlg.exec_()
            
    def _addMachineToDeployedList(self, ip_address, comment, host):
        '''Adds the given machine to the list of the user deployed ones'''
        itm = QTreeWidgetItem()
        itm.setText(0, ip_address)
        itm.setText(1, comment)
        itm.setText(2, host)
        self._mywindow.tw_deployed.addTopLevelItem(itm)

    def removeFromDeployedList(self, ip_address):
        '''Removes the entry in the deployed list for the given ip address'''
        for i in range(self._mywindow.tw_deployed.topLevelItemCount()):
            current = self._mywindow.tw_deployed.topLevelItem(i).text(0)
            if current == ip_address:
                self._mywindow.tw_deployed.takeTopLevelItem(i)
                break

    @Slot()
    def connectToSelected(self):
        '''Connects to the selected machine using remote desktop'''
        for item in self._mywindow.tw_deployed.selectedItems():
            ip_address = item.text(0)
            self.connect(ip_address)

    @Slot()
    def connectToSelectedFromRunning(self):
        '''Connects to the machines selected from the running vms list'''
        for item in self._mywindow.tw_running_vms.selectedItems():
            ip_address = item.text(0)
            self.connect(ip_address)

    @Slot()
    def deallocateSelected(self):
        '''Deallocates the selected virtual machines'''
        for item in self._mywindow.tw_running_vms.selectedItems():
            ip_address = item.text(0)
            machine_id = item.text(4)
            blade = item.text(5)
            deallocate(blade, machine_id)
            self.removeFromDeployedList(ip_address)
        self.loadRunningVmsFromSelectedHost()

    @Slot()
    def loadTemplatesList(self):
        '''Loads the list of templates from the selected host'''
        self._progress_dlg.reportProgress("Fetching templates")
        self._progress_dlg.show(cancellable=False)
        host = resolveHost(self._mywindow.cb_blades.currentText())
        templates = Queue.Queue()
        work = Thread(target=listTemplatesWorker, args=(host, templates,))
        work.start()
        self._waitForTask(work)
        response = templates.get()
        self._mywindow.lv_templates.clear()
        for image in response['base_images']:
            self._mywindow.lv_templates.addItem(image['base_image_name'])
        
        self._progress_dlg.close()

    def _waitForTask(self, tasks, progress_msgs=None, abort_event=None):
        '''Waits for the given thread to finish reporting the thread progress
        thru the queue progress_msgs and handles the cancellation if cancelled
        thru the progress dialog
        FIXME: use of queue is not safe enough, call to empty() is unreliable
        according to python doc and may block, needs better solution for
        passing data between threads
        '''
        if type(tasks) != type([]):
            tasks = [tasks]
            
        while True:
            if isAlive(tasks) == False:
                break
            if not progress_msgs is None:
                if not progress_msgs.empty():
                    self._progress_dlg.reportProgress(progress_msgs.get())
            #when user cancels
            if self._progress_dlg.getResult() == 0:
                if not abort_event is None:
                    abort_event.set()
                break
            APP.processEvents()
            time.sleep(0)
                
if __name__ == '__main__':
    APP = QApplication("abc")

    KVM_UI = KvmUI()
    KVM_UI.show()
    KVM_UI.showHideRunningVms()
    KVM_UI.setComment(getpass.getuser() + " testing")
    APP.exec_()
