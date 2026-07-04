# pcb-100mm-slider-i2c

This [slider](https://www.adafruit.com/product/5295) from Adafruit is cool, but it has a problem. It is too small.

![Adafruit Sliders](./assets/IMG_1242.JPG)

It has 65mm of travel distance for the slider movement.

Fortunately, it was easy to find a longer slider.

![new slider](./assets/IMG_1247.JPG)

This is the PTB0143-2010BPA103, in Bourn's PTB Series. It is a Low Profile Slide Potentiometer.

It has a whopping 100mm of travel! Here are some other specs:

Resistance: 10 kOhms
Tolerance: 20%	
Taper: Linear
Life: 15,000 Cycles

15k cycles is pretty nice! I've already used 3 of them. 14,997 until it starts to wear out! Wahoo!

It's an awesome party, but we still have a problem. It's not attached to a PCB, so it doesn't have an I2C interface to actually start working with it.

I often see PCBWay sponsoring YouTubers that I like, so I figured that would be a great direction to go with them for this project too!

![pcbway](./assets/pcbway.png)

There's a lot to explain before we can send the design to PCBWay.

The first thing to cover is how a potentiometer works.

And to understand that, let's review a simple voltage divider.

![](./assets/515c8377ce395fa71d000000.png)


The formula is:

```
Vout = Vin*R2/(R1+R2) 
```

So it lets you split voltages over resistors in series.

Here is an example with some voltage numbers.

![](./assets/fixedvoltdiv.png)

A slide potentiometer is basically just a variable resistor. So it is a resistor that goes between 0 and 10k ohms as you slide it.

![](./assets/var%20resistor.png)


They even show circuit diagrams like these straight in the [Bourns slider datasheet.](https://www.bourns.com/docs/Product-Datasheets/PTB.pdf)


I drew this diagram to help compare.

![](./assets/slide%20pot%20schematic.png)

