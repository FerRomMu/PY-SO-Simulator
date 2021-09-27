#!/usr/bin/env python

from hardware import *
import log

#Estos son estados de pcb
RUNNING = 2
READY = 1
NEW = 0
WAITING = 3

## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)

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


class NewInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        # carga
        prg = irq.parameters
        baseDir = self.kernel.loader().load(prg)
        pid = self.kernel.pcbTable().getNewPID()
        pcb = PCB(pid, baseDir, path=prg.name)
        self.kernel.pcbTable().add(pcb)

        # ejecucion
        if self.kernel.pcbTable().isRunningPCB():
            pcb.setState(READY)
            self.kernel.readyQueue().enqueue(pcb)
        else:
            pcb.setState(RUNNING)
            self.kernel.dispatcher().load(pcb)
            self.kernel.pcbTable().setRunningPCB(pcb)


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        HARDWARE.cpu.pc = -1  ## dejamos el CPU IDLE


class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = {'pc': HARDWARE.cpu.pc}  # porque hacemos esto ???
        HARDWARE.cpu.pc = -1  ## dejamos el CPU IDLE
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        log.logger.info(self.kernel.ioDeviceController)


class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        HARDWARE.cpu.pc = pcb['pc']
        log.logger.info(self.kernel.ioDeviceController)


class ReadyQueue():

    def __init__(self):
        self._readyQueue = []

    # indica si la cola está vacía
    def isEmpty(self):
        return not self._readyQueue

    # agrega un programa al final de la cola
    def enqueue(self, program):
        self._readyQueue.append(program)

    # remueve el primer elemento de la cola
    def dequeue(self):
        if not self.isEmpty():
            self._readyQueue.pop(0)

    # devuelve el primer elemento de la cola
    def first(self):
        if not self.isEmpty():
            return self._readyQueue[0]

    @property
    def readyQueue(self):
        return self._readyQueue


class PCB():

    def __init__(self, pid, baseDir, path):  # se inicializan siempre igual -> state, pc
        self._pid = pid
        self._baseDir = baseDir
        self._pc = 0
        self._state = NEW
        self._path = path

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

    # setter para cambiar de estado
    ##@state.setter
    def setState(self, newState):
        self._state = newState


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
        HARDWARE.cpu.pc = 0
        HARDWARE.mmu.baseDir = pcb.baseDir

    def save(self, pcb):
        pcb.baseDir += HARDWARE.cpu.pc
        HARDWARE.cpu.pc = -1


# emulates the core of an Operative System
class Kernel():

    def __init__(self):
        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        # cola de listos para ciclo de ejecución multiprogramación
        self._readyQueue = ReadyQueue()

        # tabla PCB
        self._pcbTable = PCBTable()

        # loader
        self._loader = Loader()

        # dispatcher
        self._dispatcher = Dispatcher()

    # para obtenerlos desde otras clases
    def loader(self):
        return self._loader

    def pcbTable(self):
        return self._pcbTable

    def readyQueue(self):
        return self._readyQueue

    def dispatcher(self):
        return self._dispatcher

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
    def run(self, program):
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
