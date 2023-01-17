#!/usr/bin/env python

from hardware import *
from designer import *
from time import sleep
import log

#Estos son estados de pcb
RUNNING = "RUNNING"
READY = "READY"
NEW = "NEW"
WAITING = "WAITING"
TERMINATED = "TERMINATED"

## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)
        self._priority = 0

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    @property
    def priority(self):
        return self._priority

    def setPriority(self, priority):
        self._priority = priority

    def __repr__(self):
        return "Program({name}, {instructions})".format(name=self._name, instructions=self._instructions)


## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            # print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)

    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(
            deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)


## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))

    # método para correr siguiente ciclo en #KILL #IO_IN
    def runNextCicle(self):
        if not self.kernel.scheduler.isEmptyQ():         # si hay un proceso en espera
            nextPCB = self.kernel.scheduler.getNext()    # el primer pcb en la readyQueue
            self.runProcess(nextPCB)

    # método para correr o dejar en readyQ proceso en #NEW #IO_OUT
    def runNextProcess(self, pcbToAdd):
        if self.kernel.pcbTable.isRunningPCB():
            runningPCB = self.kernel.pcbTable.runningPCB
            if self.kernel.scheduler.mustExpropiate(runningPCB, pcbToAdd):  # si hay que expropiar
                self.contextSwitch(pcbToAdd)                                # hace el context switch
            else:                                                           # sino
                pcbToAdd.setState(READY)                                    # cambia estado a READY
                self.kernel.scheduler.add(pcbToAdd)                         # agrega el pcb a la readyQ
        else:
            self.runProcess(pcbToAdd)

    # lleva a cabo el context switch entre pcb
    # hay un pcb en estado running en la pcbTable
    def contextSwitch(self, pcbToAdd):
        exPCB = self.kernel.pcbTable.runningPCB
        exPCB.setState(READY)
        self.kernel.dispatcher.save(exPCB)        # guarda el estado pcb (actualiza el pc)
        self.kernel.scheduler.add(exPCB)          # lo agrega a la readyQ
        self.runProcess(pcbToAdd)                 # corre el siguiente pcb


    # pone a correr un pcb
    def runProcess(self, pcb):
        HARDWARE.timer.reset()
        pcb.setState(RUNNING)                    # cambia estado de pcb a running
        self.kernel.dispatcher.load(pcb)         # carga el pcb en memoria
        self.kernel.pcbTable.setRunningPCB(pcb)  # establece el pcb como runningPCB


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        # carga
        path = irq.parameters[0]
        priority = irq.parameters[1]
        pid = self.kernel.pcbTable.getNewPID()
        pcb = PCB(pid, path, priority)
        #self.kernel.loader.load(pcb) no debería cargar nada
        self.kernel.pcbTable.add(pcb)

        # ejecucion
        self.runNextProcess(pcb)


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        # fin de proceso
        log.logger.info(" Program Finished ")
        pcb = self.kernel.pcbTable.runningPCB
        self.kernel.dispatcher.save(pcb)
        pcb.setState(TERMINATED)
        pt = pcb.pageTable
        self.kernel.memoryManager.freeFrames(pt.values())
        self.kernel.pcbTable.setRunningPCB(None)

        # siguiente ciclo de ejecución (si hay procesos en readyQueue)
        self.runNextCicle()


class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = self.kernel.pcbTable.runningPCB
        self.kernel.dispatcher.save(pcb)
        self.kernel.pcbTable.setRunningPCB(None)
        pcb.setState(WAITING)

        # ejecución en el IoDevice
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        log.logger.info(self.kernel.ioDeviceController)

        # siguiente proceso esperando tiempo de CPU
        self.runNextCicle()


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        log.logger.info(self.kernel.ioDeviceController)

        #siguiente
        self.runNextProcess(pcb)


class TimeoutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        HARDWARE.timer.reset()
        if not self.kernel.scheduler.isEmptyQ():
            nextPCB = self.kernel.scheduler.getNext()
            self.contextSwitch(nextPCB)


class StatInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        DESIGNER.printGantt(self.kernel.pcbTable, self.kernel.scheduler.readyQ, HARDWARE.clock.currentTick)


class PageFaultInterruptionHandler(AbstractInterruptionHandler):
    
    def execute(self, irq):
        pcb = self.kernel.pcbTable.runningPCB
        frame = self._kernel.loader.loadNextFrame(irq.parameters, pcb)
        HARDWARE.mmu.setPageFrame(irq.parameters, frame)


class PCB():

    def __init__(self, pid, path, priority):  # se inicializan siempre igual -> state, pc
        self._pid = pid
        self._pageTable = dict()
        self._pc = 0
        self._state = NEW
        self._path = path
        self._priority = priority

    @property
    def pid(self):
        return self._pid

    @property
    def pageTable(self):
        return self._pageTable
    
    @property
    def pc(self):
        return self._pc

    @property
    def state(self):
        return self._state

    @property
    def path(self):
        return self._path

    @property
    def priority(self):
        return self._priority

    # setter para cambiar de estado
    ##@state.setter
    def setState(self, newState):
        self._state = newState

    def setPc(self, pc):
        self._pc = pc
    
    def setPageTable(self, pt):
        self._pageTable = pt

    def addPageToTable(self, page, frame):
        self._pageTable[page] = frame
        for page in self._pageTable:
            log.logger.info("Page {pag} in frame: {fr}".format(pag=page, fr=self._pageTable[page]))

    def removePageFromTable(self, page):
        del self._pageTable[page]
        log.logger.info("Se debería haber eliminado la page {pag}".format(pag=page))
        for pg in self._pageTable:
            log.logger.info("La pagina es {pag} y esta en el frame {fr}".format(pag=pg, fr=self._pageTable[pg]))
    
    def __repr__(self):
        return "PCB {}".format(self._pid)


class PCBTable():

    def __init__(self):
        self._pcbTable = []
        self._runningPCB = None
        self._pidNr = -1

    # indica si el pcbTable es vacío
    def isEmpty(self):
        return not self._pcbTable

    # devuelve el pcb con pid
    def get(self, pid):
        i = 0
        while self._pcbTable[i].pid != pid and not self.isEmpty():
            i += 1
        return self._pcbTable[i].pid

    # agrega un pcb a la tabla
    def add(self, pcb):
        self._pcbTable.append(pcb)

    # elimina el pcb con pid de la tabla
    def remove(self, pid):
        i = 0
        while self._pcbTable[i].pid != pid and not self.isEmpty():
            i += 1
        self._pcbTable.pop(i)

    @property
    def runningPCB(self):
        return self._runningPCB

    ##@setRunningPCB.setter
    def setRunningPCB(self, pcb):
        self._runningPCB = pcb

    def isRunningPCB(self):
        return self._runningPCB is not None

    def getNewPID(self):
        self._pidNr += 1
        return self._pidNr
    # devuelve el número único de pid a asignar

    def allPCBs(self):
        return self._pcbTable
    
    def getPCB(self, pid):
        i = 0
        while self._pcbTable[i].pid != pid and not self.isEmpty():
            i += 1
        return self._pcbTable[i]


class Loader():

    def __init__(self, mm, fileSystem):
        self._mm = mm
        self._fileSystem = fileSystem
        self._killAlgorithm = mm.killAlgorithm()

    def loadNextFrame(self, pageToLoad, pcb):
        frameSize = self._mm.frameSize
        
        #Quiero ver si esta en swap si no tengo que leer el archivo
        if self._mm.isInSwap(pcb.pid, pageToLoad):
            prg = self._mm.getFromSwap(pcb.pid, pageToLoad)
        else:
            prg = self._fileSystem.readFromTo(pcb.path, pageToLoad, frameSize)
        
        frame = self._mm.allocFrame()
        
        i=0
        for inst in prg:
            HARDWARE.memory.write((frame*frameSize) + i, inst)
            log.logger.info("page: {p} - offset: {cel} - instr: {instr}".format(p=pageToLoad, cel=i, instr=inst))
            i+=1

        pcb.addPageToTable(pageToLoad, frame)
        self._killAlgorithm.newFrame(pcb, pageToLoad, frame)
        return frame


class Dispatcher():

    def load(self, pcb):
        log.logger.info("Cargando PCB: {} ".format(pcb))
        HARDWARE.cpu.pc = pcb.pc
        HARDWARE.mmu.resetTLB()
        pt = pcb.pageTable
        for key in pt:
            HARDWARE.mmu.setPageFrame(key,pt[key])

    def save(self, pcb):
        log.logger.info("Actualizando PCB: {} ".format(pcb))
        pcb.setPc(HARDWARE.cpu.pc)
        HARDWARE.cpu.pc = -1


class Scheduler():

    def __init__(self):
        self._readyQ = []

    # indica si la cola está vacía
    def isEmptyQ(self):
        return not self._readyQ

    # agrega un programa al final de la cola
    def enqueue(self, program):
        self._readyQ.append(program)

    # remueve el primer elemento de la cola
    def getNext(self):
        if not self.isEmptyQ():
            return self._readyQ.pop(0)

    @property
    def readyQ(self):
        return self._readyQ

    # retorna falso para los schedulers no expropiativos
    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        return False


class FCFSScheduler(Scheduler):

    def add(self, pcb):
        self.enqueue(pcb)


class PriorityScheduler(Scheduler):

    ##Por default no tiene aging
    ##Al instanciar se debe enviar true y la cantidad de ticks que modifican en 1 la prioridad
    ##para que tenga aging
    def __init__(self, aging=False, ticksAge=5):
        Scheduler.__init__(self)
        self._hasAging = aging
        self._ticksAge = ticksAge
        self._priorityDict = dict()

    def add(self, pcb):
        i = 0
        size = len(self._readyQ)
        while i != size and self.priorityElement(i) <= pcb.priority:
            i += 1
        self._readyQ.insert(i, pcb) ##Pone el pcb en la fila
        self._priorityDict[pcb.pid] = HARDWARE.clock.currentTick

    def priorityElement(self, i):
        if self._hasAging:
            ##Suma la prioridad del pcb menos el plus por tiempo en la queue
            return self._readyQ[i].priority - self.plusAge(self._readyQ[i].pid)
        else:
            ##Ignora el tiempo en la queue
            return self._readyQ[i].priority

    def plusAge(self, id):
        ##Tick actual menos el tick desde el cual espera dividido enteramente por el tickAge
        timeIn = self._priorityDict[id]
        return (HARDWARE.clock.currentTick - timeIn)//self._ticksAge


class PreemptivePriorityScheduler(PriorityScheduler):

    def mustExpropiate(self, pcbInCPU, pcbToAdd):
        return pcbInCPU.priority > pcbToAdd.priority


class RoundRobin(Scheduler):

    def __init__(self, quantum):
        Scheduler.__init__(self)
        HARDWARE.timer.quantum = quantum

    def add(self, pcb):
        self.enqueue(pcb)


class FileSystem():

    def __init__(self):
        self._files = dict()

    def write(self, path, prg):
        log.logger.info("writing file {path} with {prg}".format(path=path, prg=prg))
        self._files[path] = prg

    # retorna el archivo (o programa) asociado al path
    def read(self, path):
        try:
            prg = self._files[path]
        except:
            prg = None
            log.logger.info("No file found in path {}".format(path))

        if not (prg is None):
            log.logger.info("reading path: {p} ,file found: {f} ".format(p=path,f=prg))
            return prg

    def readFromTo(self, path, page, size):
        try:
            prg = self._files[path]
        except:
            prg = None
            log.logger.info("No file found in path {}".format(path))

        if not (prg is None):
            firstInst = page * size
            lastInst = firstInst + size
            instr = prg.instructions[firstInst:lastInst]
            log.logger.info("reading from path: {p}, instructions: {f}".format(p=path, f=instr))
            return instr

class MemoryManager():

    def __init__(self, frameSize, fs, killer):
        self._fileSystem = fs
        self._frameSize = frameSize
        self._killer = killer
        #lista de tuplas que recuerda que pcbs tienen paginas en swap
        #con forma (pid, pageEnSwap)
        self._inSwap = []
        self._swap = self.createSwap()
        self._swapSize = HARDWARE.memory.size // 2
        self._freeMemory = HARDWARE.memory.size
        self._freeFrames = self.generateFrames()
    
    #SWAP ----
    def isInSwap(self, pid, page):
        i=0
        while i < len(self._inSwap) and self._inSwap[i] != (pid, page):
            i += 1
        return i < len(self._inSwap)
        
    def createSwap(self):
        self._fileSystem.write("swapFile.sys", [])
        return "swapFile.sys"
         
    def getFromSwap(self, pid, page):
        swap = self._fileSystem.read(self._swap)
        i=0
        while i <len(swap) and not (swap[i][0] == pid and swap[i][1] == page):
            i+=1
        if i<len(swap):
            data = swap[i][2]
            self._inSwap.pop(i)
            swap.pop(i)
        else:
            raise Exception("No existe en swap: page {pag} de pcb {id}".format(pag=page, id=pid))
        self._fileSystem.write(self._swap, swap)
        return data

    #FRAMES----
    # genera los frames iniciales
    def generateFrames(self):
        frameAmount = self._freeMemory // self._frameSize   # // es para div entera
        freeFrames = []
        for elem  in range(0 ,frameAmount):
            freeFrames.append(elem)        
        return freeFrames

    def allocFrame(self):
        if self.framesAvailable() >= 1:                                  # si el nr de frames está disponible
            allocatedFrame = self._freeFrames.pop(0)                     # guarda los frames a utilizar por el proceso
        else:
            swap= self._fileSystem.read(self._swap)
            #hay suficiente espacio en swap
            if len(swap) < self._swapSize:
                #Obtiene el pcb y page del frame a matar
                toKill = self._killer.nextToKill()
                #crea una tuple que tenga la data para el swap (pid, page, data)
                frameToKill = (toKill[0].pid, toKill[1], self.dataToKill(toKill[2]))
                #guarda en el swap y al in swap, luego actualiza el archivo swap
                swap.append(frameToKill)
                self._inSwap.append((frameToKill[0], frameToKill[1]))
                self._fileSystem.write(self._swap, swap)
                #liberado el frame, lo guarda para retornarlo
                allocatedFrame = toKill[2]
                log.logger.info("Swap needed")
            else:
                # si no hay frames disponibles y no hay espacio en swap lanza excepción
                raise Exception("memory full: frames available = {fa}, required frames = {fr}".format(fa=self.framesAvailable(), fr=frames))
        log.logger.info("allocatedFr = {}".format(allocatedFrame))   # los muestra en pantalla
        log.logger.info("freeFrames = {}".format(self._freeFrames))   # muestra los frames libres restantes
        return allocatedFrame                                       # retorna los frames a utilizar

    def dataToKill(self, frame):
        data = []
        for i in range(self._frameSize):
            direccion = frame * self._frameSize + i
            data.append(HARDWARE.memory.read(direccion))
        return data

    def freeMemory(self):
        return self._freeFrames * self._frameSize

    @property
    def frameSize(self):
        return self._frameSize

    @property
    def freeFrames(self):
        return self._freeFrames

    def freeFrames(self, frames):
        for frame in frames:
            self._freeFrames.insert(0, frame)
        log.logger.info("freeFrames = {}".format(self._freeFrames))  # muestra los frames libres restantes

    def framesAvailable(self):
        return len(self._freeFrames)
    
    #killer
    def killAlgorithm(self):
        return self._killer


class KillAlgorithm():

    def __init__(self):
        self._orderPcb = []
    
    def newFrame(self, pcb, page, frame):
        self._orderPcb.append((pcb, page, frame))

class KillFifo(KillAlgorithm):

    def nextToKill(self):
        toKill = self._orderPcb.pop(0)
        toKill[0].removePageFromTable(toKill[1])
        return toKill


# emulates the core of an Operative System
class Kernel():

    def __init__(self, sch, frames, killer):
        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        timeoutHandler = TimeoutInterruptionHandler(self)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeoutHandler)

        statHandler = StatInterruptionHandler(self)
        HARDWARE.interruptVector.register(STAT_INTERRUPTION_TYPE, statHandler)

        pageFaultHandler = PageFaultInterruptionHandler(self)
        HARDWARE.interruptVector.register(PAGE_FAULT_INTERRUPTION_TYPE, pageFaultHandler)

        self._fileSystem = FileSystem()

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        # tabla PCB
        self._pcbTable = PCBTable()

        # dispatcher
        self._dispatcher = Dispatcher()

        # scheduler
        self._scheduler = sch

        # configuración frames
        self._mm = MemoryManager(frames, self._fileSystem, killer)
        HARDWARE.mmu.frameSize = frames

        # loader
        self._loader = Loader(self._mm, self._fileSystem)


    # getters para obtenerlos desde otras clases
    @property
    def loader(self):
        return self._loader

    @property
    def pcbTable(self):
        return self._pcbTable

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    @property
    def memoryManager(self):
        return self._mm
    
    @property
    def fileSystem(self):
        return self._fileSystem

    ## emulates a "system call" for programs execution
    def run(self, path, priority):
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, [path, priority])
        HARDWARE.cpu._interruptVector.handle(newIRQ)

    def runWithDelay(self, path, priority, ticks):
        sleep(ticks)
        self.run(path, priority)

    def __repr__(self):
        return "Kernel "
