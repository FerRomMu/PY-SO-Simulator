import log
from so import *

##un objeto que haga "marcos" y otras utilidades con el logger a fines esteticos
class LoggerDesign():

    def __init__(self):
        self._proceso = ["|Proceso   |"]
        self._queue = ["|ReadyQ    |"]

    def printGantt(self, table, tick):
        self.actualizarProcesos(table, tick)
        self.actualizarQueue(table, tick)
        self.title("DIAGRAMA DE GANTT")
        self.printBar()
        for text in self._proceso:
            log.logger.info(text)
        self.printBar()
        for text in self._queue:
            log.logger.info(text)

    #imprime una barra de largo 80
    def printBar(self):
        log.logger.info("|==============================================================================|")

    #imprime titulo de 3 renglones, con texto centrado
    def title(self, title):
        self.printBar()
        self.centerMessage(title)
        self.printBar()
        print()

    #imprime texto centrado
    def centerMessage(self, message):
        log.logger.info("|" + message.center(78) + "|")

    def actualizarProcesos(self, table, tick):
        #guardo el tick como string
        tickFormat = "{}".format(tick)
        #quito primer columna de la tabla
        self._proceso[0] = self._proceso[0][12:]
        #relleno la tabla con espacios
        self._proceso[0] = self._proceso[0].rjust(68)
        #agrego el nuevo tick
        self._proceso[0] = self._proceso[0] + tickFormat.center(3) + "|"
        #recupero la columna borrada y agrego el resto del renglon
        self._proceso[0] = "|Proceso  |" + self._proceso[0][3:]

        i = 1
        for pcb in table.allPCBs():
            #si el pcb no esta en la tabla de gantt
            pcbid = "{}".format(pcb.pid)
            pcbid = "|" + pcbid.rjust(9) + "|"
            if pcb.state == "RUNNING":
                state = "CPU|"
            else:
                state = " - |"
            if i+1 > len(self._proceso):
                #genero nueva linea
                newLine = pcbid + state.rjust(69)
                #la agrego como otro renglon de la tabla
                self._proceso.append(newLine)
            else:
                self._proceso[i] = self._proceso[i][12:]
                self._proceso[i] = self._proceso[i].rjust(68)
                self._proceso[i] = self._proceso[i] + state
                self._proceso[i] = pcbid + self._proceso[i][3:]
            i = i + 1

    def actualizarQueue(self, table, tick):
        tickFormat = "{}".format(tick)
        self._queue[0] = self._queue[0][12:]
        self._queue[0] = self._queue[0].rjust(68)
        self._queue[0] = self._queue[0] + tickFormat.center(3) + "|"
        self._queue[0] = "|ReadyQ   |" + self._queue[0][3:]


DESIGNER = LoggerDesign()