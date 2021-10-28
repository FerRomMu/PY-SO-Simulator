#!/usr/bin/env python

from hardware import *
from designer import *
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
        prg = irq.parameters
        baseDir = self.kernel.loader.load(prg)
        pid = self.kernel.pcbTable.getNewPID()
        priority = prg.priority
        pcb = PCB(pid, baseDir, prg.name, priority)
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
        DESIGNER.printGantt(self.kernel.pcbTable, HARDWARE.clock.currentTick)


class PCB():

    def __init__(self, pid, baseDir, path, priority):  # se inicializan siempre igual -> state, pc
        self._pid = pid
        self._baseDir = baseDir
        self._pc = 0
        self._state = NEW
        self._path = path
        self._priority = priority

    @property
    def pid(self):
        return self._pid

    @property
    def baseDir(self):
        return self._baseDir

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

    def __repr__(self):
        return "PCB {}".format(self.pid)

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


class Loader():

    def __init__(self):
        self._nextDir = 0

    def load(self, prg):
        # loads the program in main memory
        progSize = len(prg.instructions)
        for index in range(0, progSize):
            inst = prg.instructions[index]
            HARDWARE.memory.write(index + self._nextDir, inst)
        self._nextDir += progSize
        return self._nextDir - progSize


class Dispatcher():

    def load(self, pcb):
        log.logger.info("Cargando PCB: {} ".format(pcb))
        HARDWARE.cpu.pc = pcb.pc
        HARDWARE.mmu.baseDir = pcb.baseDir

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

    def add(self, pcb):
        i = 0
        size = len(self._readyQ)
        while i != size and self.priorityElement(i) <= pcb.priority:
            i += 1
        self._readyQ.insert(i, [pcb, HARDWARE.clock.currentTick]) ##Guarda el tick en el que se agrego a la lista

    def getNext(self):
        if not self.isEmptyQ():
            return self._readyQ.pop(0)[0]

    def priorityElement(self, i):
        if self._hasAging:
            ##Suma la prioridad del pcb menos el plus por tiempo en la queue
            return self._readyQ[i][0].priority - self.plusAge(self._readyQ[i][1])
        else:
            ##Ignora el tiempo en la queue
            return self._readyQ[i][0].priority

    def plusAge(self, timeIn):
        ##Tick actual menos el tick desde el cual espera dividido enteramente por el tickAge
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

# emulates the core of an Operative System
class Kernel():

    def __init__(self, sch):
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

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        # tabla PCB
        self._pcbTable = PCBTable()

        # loader
        self._loader = Loader()

        # dispatcher
        self._dispatcher = Dispatcher()

        # scheduler
        self._scheduler = sch



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

    """ Obsoleto
    def load_program(self, program):
        # loads the program in main memory
        progSize = len(program.instructions)
        for index in range(0, progSize):
            inst = program.instructions[index]
            HARDWARE.memory.write(index, inst)
    """

    ## emulates a "system call" for programs execution
    # pasa la prioridad al program
    def run(self, program, priority):
        program.setPriority(priority)
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, program)
        HARDWARE.cpu._interruptVector.handle(newIRQ)

    """
    ## emulates a "system call" for programs execution
    def run(self, program):
        self.load_program(program)
        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)

        # set CPU program counter at program's first intruction
        HARDWARE.cpu.pc = 0
    """

    def __repr__(self):
        return "Kernel "
