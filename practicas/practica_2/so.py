#!/usr/bin/env python

from hardware import *
import log



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


## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))


# emulates a waiting Queue for processing
class WaitQueue():
    _queue = []

    def __init__(self):
        self._queue = []

    # agrega programas a la cola de espera
    def enqueue(self, programs):
        self._queue.extend(programs)

    # retorna verdadero si la cola es vacía
    def isEmpty(self):
        return not self._queue()

    # borra el primer elemento de la cola
    def dequeue(self):
        self._queue.pop(0)

    # retorna el primer elemento de la cola
    def first(self):
        return self._queue(1)

    @property
    def queue(self):
        return self._queue


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        _waitQueue = WaitQueue()
        log.logger.info(" Program Finished ")
        # por ahora apagamos el hardware porque estamos ejecutando un solo programa
        if _waitQueue.isEmpty:
            HARDWARE.switchOff()

# emulates the core of an Operative System
class Kernel():
    _waitQueue = WaitQueue()

    def __init__(self):
        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)


    def load_program(self, program):
        # loads the program in main memory  
        progSize = len(program.instructions)
        for index in range(0, progSize):
            inst = program.instructions[index]
            HARDWARE.memory.write(index, inst)

    ## emulates a "system call" for programs execution  
    def run(self, program):
        self.load_program(program)
        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)

        # set CPU program counter at program's first intruction
        HARDWARE.cpu.pc = 0

    # emulates a "system call" for batch execution
    def executeBatch(self, programs):
        self._waitQueue.enqueue(programs)  # adds batch in waiting queue except first prg
        for program in programs:
            self.run(program)
            self._waitQueue.dequeue()

    def __repr__(self):
        return "Kernel "


