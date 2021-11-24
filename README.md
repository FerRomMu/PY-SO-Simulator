# grupo_5

### Integrantes:

| Nombre y Apellido              |      Mail                      |     usuario Gitlab   |
| -----------------------------  | ------------------------------ | -------------------  |
|   Juan Cruz Insaurralde        |juancruzinsaurralde@outlook.com |     juann47          |
|   Romero Muñoz Fernando        |fer.rom.mu@gmail.com            |     fer.rom.mu       |
|                                |                                |                      |



## Entregas:

### Práctica 1: Aprobada  

### Práctica 2: Aprobada  
 Solo un comentario para tener en cuenta en la P3 (el proceso que esta corriendo debe ser desencolado antes de mandarlo a la CPU... en esta practica esta bien lo que hicieron)




### Práctica 3: Aprobada 

<details><summary>Corregido</summary>
Les esta funcionando pero no es lo que debe hacer... hay un tema en el dispatcher que me parece los confunde (hablemoslo en clase)

>  El BaseDir del Proceso no cambia (esta siempre cargado en el mismo lugar) ... lo que va cambiando es el pc (la instruccion a ejecutar)


- Dispatcher: 

    Que estan haciendo aca?? : https://gitlab.com/so-unq-2021-s2/grupo_5/-/blob/main/practicas/practica_3/so.py#L313 

    y aca???: https://gitlab.com/so-unq-2021-s2/grupo_5/-/blob/main/practicas/practica_3/so.py#L309





- KillInterruptionHandler: 

 esto no es necesario (lo tiene que hacer el Dispatcher) - saquen esta linea
https://gitlab.com/so-unq-2021-s2/grupo_5/-/blob/main/practicas/practica_3/so.py#L140     


</details>



##### Algunos Comentarios: (no es que esto esté mal, los pueden hacer en la P4)

- https://gitlab.com/so-unq-2021-s2/grupo_5/-/blob/main/practicas/practica_3/so.py#L104:  podrian hacer que el dequeue() desencole y retorne el elemento directamenrte (se evitan hacer 2 operaciones first + dequeue)

- Correccion del comentario: "se carga en la CPU":  https://gitlab.com/so-unq-2021-s2/grupo_5/-/blob/main/practicas/practica_3/so.py#L107


- Loader:  https://gitlab.com/so-unq-2021-s2/grupo_5/-/blob/main/practicas/practica_3/so.py#L296

     podrian guardarse la baseDir antes de cargar el programa (asi evitan restar lo que sumaron en la linea superior)

```
     baseDir = self._nextDir 
     ... cargo las instrucciones en memoria ...
     return baseDir
```




### Práctica 4: Aprobada 


### Práctica 5: Aprobada 

##### Comentarios:

https://gitlab.com/so-unq-2021-s2/grupo_5/-/blob/main/practicas/practica_5/so.py#L486

La creacion de los Free Frames la  podrían hacer mas simple con un for:


```
        for elem  in range(0 ,cantFrames):
            result.append(elem
```
)


