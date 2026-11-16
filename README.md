# Rune Factory 4 Special en español (castellano)

Traducción no oficial al español de España de **Rune Factory 4 Special** (PC/Steam).

## ⚠️ Aviso: traducción hecha con inteligencia artificial

Este parche está hecho **por fans y para fans** de la saga que llevamos años esperando
una traducción al español que nunca llegó. Rune Factory 4 Special salió en inglés,
francés, alemán, japonés, coreano y chino… pero no en español.

**La traducción se ha generado con inteligencia artificial**, usando el texto oficial en
inglés y, como apoyo, la localización oficial francesa (para el tú/usted, el género y
los matices). Se ha revisado por muestreo y se ha probado en el juego, pero **no** se han
revisado a mano las más de 100.000 líneas. Puede haber errores, frases poco naturales o
alguna concordancia de género incorrecta. Si encuentras alguno, abre un *issue* con la
frase original y la traducida.

No está afiliado ni respaldado por Marvelous, XSEED ni ninguna otra empresa. Necesitas
tu propia copia legal del juego en Steam; este repositorio no incluye ningún archivo del
juego.

## Qué está traducido

- Todo el guion: historia, conversaciones diarias, eventos, citas y bodas, festivales
  (unas 113.000 líneas).
- Menús, nombres y descripciones de objetos, monstruos, lugares, habilidades, encargos,
  modo Recién casados, logros y opciones de la versión de PC.
- Concordancia con el sexo del protagonista (Lest/Frey) donde el español la necesita.

**Sigue en inglés:** el texto dibujado dentro de imágenes (botones del menú de título,
cabeceras como «LOAD», botones Yes/No y algunos rótulos).

## Instalación

Requisitos: [Python 3](https://www.python.org/downloads/) y el juego cerrado.

1. Descarga este repositorio (botón **Code → Download ZIP**) y descomprímelo.
2. Abre una terminal en esa carpeta y ejecuta:

   ```
   python instalar.py "C:\Program Files (x86)\Steam\steamapps\common\Rune Factory 4 Special"
   ```

   (cambia la ruta si tu juego está en otra biblioteca de Steam).
3. En el juego, elige **English** como idioma: ahora aparece como «Español».

## Desinstalación

```
python desinstalar.py "C:\ruta\al\juego"
```

Deja los archivos del juego exactamente como estaban. Si Steam actualiza o verifica el
juego, la traducción se pierde: vuelve a ejecutar `instalar.py`.

## Cómo funciona

El instalador no reescribe los ~4,7 GB del juego: añade los textos traducidos al final de
`bundleMain.mbundle`/`bundlePatch2.mbundle` y redirige sus entradas en
`Bundle/Manifest.plist`, guardando copias (`*.es_backup`) para poder deshacerlo.

- `mod/texto/` — textos ya traducidos que se instalan.
- `tools/` — lectura/escritura de los archivos `.mbundle` y de las tablas de texto.
