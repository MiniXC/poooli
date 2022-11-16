# poooli

A python library for printing on the Poooli thermal printer (unofficial).
Inspired by the [blog posts by @cure_honey](https://qiita.com/cure_honey/items/dff6ac380de15aee31bf) on Poooli.

## example

```python
import bluetooth
from poooli import Poooli

socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

pli = Poooli(socket)
pli.connect("YOUR:POOLI:MAC:ADDRESS", channel=1)
pli.send_image("path/to/image.png", contrast=1.5, brightness=1.5)
```