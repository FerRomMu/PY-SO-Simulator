import log
from so import *

# --un objeto que haga "marcos" y otras utilidades con el logger a fines esteticos
class LoggerDesign():

    def __init__(self):
        # Cada elemento de la lista es un renglon a imprimir de la tabla
        self._proceso = ["|Proceso   |"]
        self._queue = ["|ReadyQ    |"]
        self._analysis = []
        self._data = []
        self._analysis.append("|Proceso   |T. Espera |T. Retorno|")

    def printGantt(self, table, readyQ, tick):
        # Actualiza lista de renglones de la tabla
        self.actualizarProcesos(table, tick)
        self.actualizarQueue(readyQ, tick)
        self.actualizarAnalysis(table)

        self.title("DIAGRAMA DE GANTT")
        # imprime todos los renglones de cada tabla
        self.printBar()
        for text in self._proceso:
            log.logger.info(text)
        self.printBar()
        for text in self._queue:
            log.logger.info(text)
        self.printBar()
        for text in self._analysis:
            log.logger.info(text)
        self.printBar()

    # imprime una barra de largo 80
    def printBar(self):
        log.logger.info("|==============================================================================|")

    # imprime titulo de 3 renglones, con texto centrado
    def title(self, title):
        self.printBar()
        self.centerMessage(title)
        self.printBar()
        print()

    # imprime texto centrado
    def centerMessage(self, message):
        log.logger.info("|" + message.center(78) + "|")

    def actualizarProcesos(self, table, tick):
        # guardo el tick como string
        tickFormat = "{}".format(tick)
        # quito primer columna de la tabla
        self._proceso[0] = self._proceso[0][12:]
        # relleno la tabla con espacios
        self._proceso[0] = self._proceso[0].rjust(68)
        # agrego el nuevo tick
        self._proceso[0] = self._proceso[0] + tickFormat.center(3) + "|"
        # recupero la columna quitada y agrego el resto del renglon
        self._proceso[0] = "|Proceso  |" + self._proceso[0][3:]

        i = 1
        for pcb in table.allPCBs():
            # si el pcb no esta en la tabla de gantt
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

    def actualizarQueue(self, readyQ, tick):
        tickFormat = "{}".format(tick)
        self._queue[0] = self._queue[0][12:]
        self._queue[0] = self._queue[0].rjust(68)
        self._queue[0] = self._queue[0] + tickFormat.center(3) + "|"
        self._queue[0] = "|ReadyQ   |" + self._queue[0][3:]

        i = 1
        for pcb in readyQ:
            pcbid = "{}".format(pcb.pid)
            pcbid = pcbid.center(3) + "|"
            # si hay mas pcbs que renglones
            if i+1 > len(self._queue):
                #genero nueva linea
                newLine = "|         |".ljust(76) + pcbid
                #la agrego como otro renglon de la tabla
                self._queue.append(newLine)
            else:
                self._queue[i] = self._queue[i][12:]
                self._queue[i] = self._queue[i].rjust(68)
                self._queue[i] = self._queue[i] + pcbid
                self._queue[i] = "|         |" + self._queue[i][3:]
            i = i + 1
        #si hay menos pcbs en queue que renglones, hay que quitar renglones
        while i < len(self._queue):
            self._queue[i] = self._queue[i][12:]
            self._queue[i] = self._queue[i].rjust(68)
            self._queue[i] = self._queue[i] + "   |"
            self._queue[i] = "|         |" + self._queue[i][3:]
            i = i + 1

    def actualizarAnalysis(self, table):
        sizeT = len(table.allPCBs())
        if table.runningPCB != None:
            pActual = table.runningPCB.pid
        else:
            pActual = -1
        if len(self._data) == sizeT:
            #hay que actualizar info
            for proceso in self._data:
                if not proceso[3]: ##Si aún no había terminado
                    if table.getPCB(proceso[0]).state == "TERMINATED": #Veo si terminó
                        proceso[3] = True
                    else: #Si no termino actualizo data
                        if proceso[0] != pActual: ##Veo si esta esperando
                            proceso[1] += 1
                        proceso[2] += 1 ##Agregar 1 al t retorno.            
        else:
            #hay que agregar pcbs nuevos
            i = len(self._data)
            while len(self._data) < sizeT:
                #pid, t espera, t retorno, ¿finalizo?
                if pActual == i:
                    t = 0
                else:
                    t = 1
                self._data.append([i,t,1, False])
                i += 1
        j = 0
        totale = 0
        totalr = 0
        self._analysis = [self._analysis[0]]
        while j < len(self._data):
            pid = str(self._data[j][0]).center(10)
            tesp = str(self._data[j][1]).center(10)
            tret = str(self._data[j][2]).center(10)
            self._analysis.append("|" + pid + "|" + tesp + "|" + tret + "|")
            totale += self._data[j][1]
            totalr += self._data[j][2]
            j += 1
        stotale = str(totale).center(3)
        stotalr = str(totalr).center(3)
        if j != 0:
            pre = totale // j
            prr = totalr // j
        else:
            pre = 0
            prr = 0
        pre = str(pre).center(3)
        prr = str(prr).center(3)
        self._analysis.append("|Total     |{te}       |{tr}       |".format(te=stotale, tr=stotalr))
        self._analysis.append("|Promedio  |{pe}       |{pr}       |".format(pe=pre, pr=prr))

DESIGNER = LoggerDesign()