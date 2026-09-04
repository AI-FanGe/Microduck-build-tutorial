# Assembly Guide

This guide provides detailed instructions on how to assemble the parts for the Microduck robot. Printing the parts and buying the necessary components are prequisites for this guide, so please refer to the [Printing Guide](printing.md) and the [BOM](bom.md) before starting the assembly process. 

At any point during the assembly, you can refer to the [Onshape assembly](https://cad.onshape.com/documents/d424992a192a8ce34ffce163/v/7de3e6e40f0e1185d169e6d9/e/b34620a03cc3a684006c5867?renderMode=0&uiState=6a2fccab8e6d9214d2644ca7) to see how the parts fit together.

The steps to assemble the robot are as follows:
1. [Motor Setup](#1-motor-setup): Configure the motors using the Dynamixel Wizard software.
2. [Cable Setup](#2-cable-setup): Prepare all the cables necessary for the assembly. 
3. [Leg Assembly](#3-leg-assembly): Assemble the legs of the robot.
4. [Torso Assembly](#4-torso-assembly): Assemble the torso and arms of the robot.
5. [Electronics](#5-electronics): Assemble the top of the trunk, build the battery module, and connect the electronics.
6. [Final Assembly](#6-final-assembly): Assemble all the parts together to complete the robot.


---

## 1. Motor Setup

The first step in the assembly process is to set up the motors. I highly recommend writing the motor IDs directly on them to avoid mixing them up during configuration and assembly. The following table lists the motor names and their corresponding IDs:

| Motor Name | ID |
|------------|----|
| Left Hip Yaw | 11 |
| Left Hip Roll | 12 |
| Left Hip Pitch | 13 |
| Left Knee | 14 |
| Left Ankle Pitch | 15 |
| Left Ankle Roll | 16 |
| Right Hip Yaw | 21 |
| Right Hip Roll | 22 |
| Right Hip Pitch | 23 |
| Right Knee | 24 |
| Right Ankle Pitch | 25 |
| Right Ankle Roll | 26 |
| Left Shoulder Pitch | 31 |
| Left Shoulder Roll | 32 |
| Left Elbow | 33 |
| Right Shoulder Pitch | 41 |
| Right Shoulder Roll | 42 |
| Right Elbow | 43 |
| Head | 51 |

To configure all the motors, connect one motor at a time to your PC using the U2D2 kit as presented in the image below. 

<img width="100%" alt="image" src="https://github.com/user-attachments/assets/240468b4-6963-4800-a00a-176226eb9185" />

<br>
<br>

Then, launch [Dynamixel Wizard](https://emanual.robotis.com/docs/en/software/dynamixel/dynamixel_wizard2/). If your XL330 motor is not new, perform a factory reset by clicking on the "Recovery" button, selecting the XL-330-288 model and following the instructions. 

In the "Option" tab, select "Protocol 2.0", "57600 bps" as the baud rate, and verify that the correct COM port is selected. Then, click on the "Scan" button to detect the motor. Once the motor is detected, you can set the following parameters (and click on the "Save" button to save the settings):
- ID: the ID of the motor as listed in the table above
- Baud Rate: 3 (1Mbps)
- Return Delay Time: 0
- PWM Slope: 255 (no slope)
- Shutdown: 52 (Removing "Bit 0 Input voltage error")

Once the parameters are set, you can disconnect the motor and move on to the next one. If you want to check the motors at the end, you can connect them together as their IDs are set. You will need to change the baud rate of the scan to 1Mbps as it as been changed during the configuration. 

---

## 2. Cable Setup

The XL330 motors used in the Microduck robot are daisy-chained, which means that the motors are connected in series. This allows to limit the number of cables that need to be routed through the robot. The only exception is near the board, where the first cables are split to connect to several links. The following diagram shows how the motors are connected to each other and to the board, and what cable lengths are used for each connection. 

<img width="100%" alt="routing" src="https://github.com/user-attachments/assets/fd655925-4968-4892-afc6-e4fe00495b89" />

### 2.1 Splitter Cable

To create the 1-to-2 splitter cable, you can cut 2 cables of 180mm to obtain 3 half-cables of approximately 50mm (you don't need more length than that). Then, you can solder 2 of them to the 3rd one. Be careful to solder together the same wires, as an incorrect connection can damage permanently the motors. Do not forget to insulate the soldered connections with heat shrink tubing. 

To do the 1-to-3 splitter cable, the process is the same, but one of the 3 outgoing cables should be longer than the other two to allow for the robot opening from the top. So you should cut 2 cables of 180mm into 3 half-cables of approximately 50mm and one half-cable of approximately 120-130mm. 

The following images shows how the splitter cable should look like.

<img width="100%" alt="image190" src="https://github.com/user-attachments/assets/9384e878-72db-4b22-9de8-bbf1af28c7f9" />

### 2.2 Reducing Cable Length

To reduce the length of the 180mm cables, you can cut them to the desired length and solder the ends back together, but it can lead to a weak connection and communication issues. A better solution is to re-crimp the cables to the desired length. To do this, you will need a crimping tool, JST EH crimp terminals, and optionally a wire stripper. You can check the [BOM](bom.md) for references.

<img width="100%" alt="image922" src="https://github.com/user-attachments/assets/e0d045f5-8e5a-4335-8f9a-7266d1a41eca" />

<br>
<br>

First, cut the cable to the desired length. The end cut to the correct length should be stripped to expose the wires on 2mm, not more. While crimping the terminals, the first crimp will be done on the plastic part of the terminal to hold the wire in place, and the second crimp will be done on the metal part of the terminal to make the electrical connection. The details of the crimping process are presented in this [video](https://youtu.be/2hUjM0x_yfw).

<p align="center">
  <img height="250px" alt="image958" src="https://github.com/user-attachments/assets/31fa1b7c-5757-465e-8c69-24e27dfedf70" />
  <img height="250px" alt="image940" src="https://github.com/user-attachments/assets/82b92448-4931-4d4c-bf3d-20253d7764bc" />
</p>

Once the 3 end terminals are crimped, you need to retrieve the plastic housing from the second half of the cable. You can do this by rising the plastic stops on the housing with a small screwdriver and pulling the housing out. If you have trouble with this step, here is another [video](https://youtu.be/mWsNwO4s6kE) showing how to do it. 

Finally, you can insert the 3 crimped terminals into the plastic housing. The order of the wires is important, so make sure to insert them in their corresponding position. Here is a last [video](https://youtu.be/w1A9wdLn3Ro) showing how to insert the terminals into the housing.


--- 

## 3. Leg Assembly

The objective of this section is to assemble the legs of the robot and fix them to the pelvis. 

<p align="center">
  <img width="80%" alt="image" src="https://github.com/user-attachments/assets/e3254867-ebaf-4d84-9591-d567e8b5ae8d" />
</p>

For the assembly, you should refer to the [Onshape assembly](https://cad.onshape.com/documents/d424992a192a8ce34ffce163/v/7de3e6e40f0e1185d169e6d9/e/b34620a03cc3a684006c5867?renderMode=0&uiState=6a2fccab8e6d9214d2644ca7) to see how the parts fit together. Nevertheless, some parts of the assembly require specific instructions and are detailed in the following sub-sections.

### 3.1 Double-Motor Blocks

For the double-motor blocks used in the ankle and hip joints of the robot, you should pay attention to the cable routing, as the motors are very close to each other. Specifically, the cable connected to the bus between the two motors should be plugged before sliding the motors into the double-motor block. It concerns the cable relying the two motors, as well as the cable connecting the double-motor block to the next motor in the chain. The following images show you the assembly process on a right ankle double-motor block. 

Cable routing before sliding the motors into the double-motor block (do not forget the spacer):

<p align="center">
  <img width="80%" alt="image" src="https://github.com/user-attachments/assets/ff3f5251-780d-4131-92e5-6077fda5364f" />
</p>

Result after sliding the motors into the double-motor block:

<p align="center">
  <img height="300px" alt="image" src="https://github.com/user-attachments/assets/516b395e-33f1-4191-89f8-fbd971a374ba" />
  <img height="300px" alt="image" src="https://github.com/user-attachments/assets/6550922b-200f-4813-9464-048147ae67f7" />
</p>

### 3.2 Cable Routing 

For the cable lengths, refers to the [Cable Setup](#2-cable-setup) section. You should use the cable sockets on the tibia, femur and hip double-motor blocks to route the cables through the robot. 
For the tibia and femur routing, you can check the first image of the section. For the hip double-motor block, you can check the image below. 

<p align="center">
  <img width="80%" alt="image" src="https://github.com/user-attachments/assets/1f9419be-4711-42d0-bb36-5c9a4933c496" />
</p>

### 3.3 Feet Adhesion

To increase the adhesion of the feet to the ground, you can add an optional layer of rubber on the bottom of the feet. You can use a rubber sheet or cut a piece of an old cycling tire. 

<p align="center">
  <img width="80%" alt="image" src="https://github.com/user-attachments/assets/85b68480-c078-4cdb-8431-d062476647ee" />
</p>

---

## 4. Torso Assembly

The objective of this section is to assemble the torso of the robot. 

<p align="center">
  <img width="80%" alt="image" src="https://github.com/user-attachments/assets/2539f053-079f-4133-9bd1-64700581052e" />
</p>

For the assembly, you should refer to the [Onshape assembly](https://cad.onshape.com/documents/d424992a192a8ce34ffce163/v/7de3e6e40f0e1185d169e6d9/e/b34620a03cc3a684006c5867?renderMode=0&uiState=6a2fccab8e6d9214d2644ca7) to see how the parts fit together. 

Once the torso is assembled, you can fix it to the pelvis and connect the splitter cables to the hip yaw motors, shoulder pitch motors, and the RPI Robot Hat.

<p align="center">
  <img width="80%" alt="image" src="https://github.com/user-attachments/assets/b63c5cef-9b47-4408-8000-87cbec58fc34" />
</p>

---

## 5. Electronics

The objective of this section is to assemble the electronics of the robot, including the battery module and the trunk top. 

The following schematic shows how the electronics are connected together. The battery module is composed of a 2S 18650 battery holder and a BMS board. It is connected to the trunk top with a xt30 connector. The trunk top contains the USB-C charger and the switch powering on the Raspberry Pi. The routing allows to charge the battery independently of the power state of the robot. The alimentation of the Raspberry Pi is done through one of the 2 JST EHR-4 connectors on the RPI Robot Hat. 

<img width="100%" alt="microduck_elec" src="https://github.com/user-attachments/assets/39c3846d-ec3d-447d-befe-7f4e0d7e2ca3" />

### 5.1 Battery Module

To assemble the battery module, first connect the 4.2V pin of the BMS to the metal contact on the battery holder, located on the side opposite the red (8.4V) and black (0V) wires. To make this easier, you can melt a small hole in the holder using your soldering iron to reach and solder the wire to the contact. Next, solder the positive (+) and negative (-) wires from the BMS to the XT30 connector. Once the wiring is complete, secure the BMS to the back of the battery holder using double-sided tape. Finally, apply hot glue to insulate all the connections and prevent any short circuits. The pictures below show the fully assembled battery module.

<p align="center">
  <img height="280px" alt="image" src="https://github.com/user-attachments/assets/810e1c1f-ad19-48c4-8fac-5c869f9a7651" />
  <img height="280px" alt="image" src="https://github.com/user-attachments/assets/54a14540-d09d-4527-a8b7-8b936ca0c0c4" />
</p>

### 5.2 Trunk Top

First, insert the switch into the trunk top. Using pliers, carefully fold its pins down to free up some vertical space.

Next, prepare the JST EHR-4 power cable for the RPI Robot Hat. Cut a Dynamixel cable to a length of approximately 150mm and remove the two unused wires. Refer to the picture below to see which wires to keep.

<p align="center">
  <img width="35%" alt="image" src="https://github.com/user-attachments/assets/e1dc34b5-98df-4ee1-861e-6f42cfd46f67" />
</p>

To wire the components, start by soldering the USB-C charger to the XT30 connector, which will be used to connect the battery module. Next, wire the switch by soldering the charger's **BAT** pin to one of its terminals, and the **VIN** wire of the JST EHR-4 cable to the other. Finally, complete the circuit by soldering the **GND** wire of the JST EHR-4 cable directly to the **GND** pin of the USB-C charger. 

The picture below shows the result of the wiring process.

<p align="center">
  <img width="60%" alt="image" src="https://github.com/user-attachments/assets/24028ff2-4bd2-4be3-9f0e-d7b23aa124b9" />
</p>

*Important:* Because the trunk top is printed in PLA (which is sensitive to heat), make sure to solder the USB-C charger module before mounting it to the plastic part. Also, once the wiring is complete, you should isolate the connections with hot glue to prevent any short circuits.

## 6. Final Assembly

To finalize the assembly of the robot, you just have to slide the battery module into the trunk, connect its XT30 connector to the trunk top, connect the JST EHR-4 cable to the RPI Robot Hat, and close the trunk with the trunk top. 

<p align="center">
  <img height="450px" alt="image" src="https://github.com/user-attachments/assets/b142e3ef-d1d4-4421-8a69-0b8b8bfef6f2" />
  <img height="450px" alt="image" src="https://github.com/user-attachments/assets/125cc2f3-b8af-479b-90ab-a38f1be22028" />
</p>

<p align="center">
  <img width="40%" alt="WhatsApp Image 2026-06-25 at 18 08 36" src="https://github.com/user-attachments/assets/4dfc1bee-20c1-46d2-b9ea-ea9a8bea072b" />
</p>

If you have followed all the steps of this guide, your robot should be fully assembled and ready to be powered on. You can now proceed to the [Deployment Guide](deployment.md) to deploy the software on the Raspberry Pi and start controlling your Microduck robot!
