# Microduck: A Compact, Fully 3D-Printable Open-Source Humanoid Robot

[![License: GPL v3](https://img.shields.io/badge/Software-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/Hardware-CC%20BY--NC--SA%204.0-orange.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.18470949-blue)](https://doi.org/10.5281/zenodo.20784789)

<p align="center">
  <img height="380px" alt="image" src="https://github.com/user-attachments/assets/e7bc975c-ab70-4ce5-a882-225468f9ffff" />
  <img height="380px" alt="image" src="https://github.com/user-attachments/assets/df0143d0-566d-44a4-a285-8507b6c01a19" />
  <img height="380px" alt="image" src="https://github.com/user-attachments/assets/11ab24f1-ea60-4219-8a92-078d78795115" />
</p>
  
Welcome to the **Microduck** project! 

Microduck is a ~30cm tall open-source humanoid robot created by [Marc Duclusaud](https://github.com/MarcDcls) as a member of the Rhoban team at LaBRI, University of Bordeaux, and designed specifically for makers, students, and robotics enthusiasts. The core philosophy behind this project is accessibility: the total cost of the robot is kept relatively low ($550-$600), all components are 3D-printable or easily sourced, and the assembly process is guided with detailed instructions. This means that anyone with a standard desktop 3D printer and a few basic tools should be able to build their own Microduck from scratch.

The idea behind Microduck is to provide a platform for learning and experimentation in robotics. By making the design open, users are encouraged to modify, improve, and share their own versions of the robot. Whether you're interested in programming, mechanical design, or electronics, Microduck offers a hands-on experience that can help you develop your skills in a fun and engaging way.

The main features of Microduck are:
*   🤖 **100% Open-Design**: Mechanics, 3D models, and documentation are entirely free to use and modify.
*   🔧 **DIY & Maker Friendly**: Guided assembly instructions, fully 3D-printable parts and cheap components.
*   📏 **Compact Size**: Microduck is only 30cm tall and can be recharged via USB-C, making it the perfect desktop companion for robotics experimentation.

To see the robot take its first steps, check out this YouTube video: [https://youtu.be/1pnFrT_jfXQ](https://youtu.be/1pnFrT_jfXQ)

---

## 🛠️ Components Overview

Here is a quick overview of what is in the robot:

| Component | Quantity | Description / Notes |
| :--- | :---: | :--- |
| **3D Printed Parts** | ~30 | Check the CAD files. Recommended material is PLA. |
| **Servo Motors** | 19 | Dynamixel XL330-M288-T servomotor. |
| **Microcontroller**| 1 | Raspberry Pi Zero 2W. |
| **Board Hat** | 1 | Pollen RPI Robot Hat for Raspberry Pi Zero 2W. |
| **Power Supply** | 2 | 18650 3.7V Lithium-ion Batteries. |
| **Battery Holder** | 1 | 2x18650 Battery Holder. |
| **USB-C Charger** | 1 | Standard USB-C charger. |
| **BMS** | 1 | Battery Management System for 2x18650 batteries. |
| **Plastic Screws**| ~200 | Standard plastic screws for assembly. |
| **Steel & POM Shims** | 12 | Alternative to needle bearings for motors without idler horns. | 

A full, detailed Bill Of Materials (BOM) with links to purchase and prices is available [here](docs/bom.md)

---

## 📁 CAD Files

<img height="350px" alt="Capture d’écran du 2026-06-15 13-33-16" src="https://github.com/user-attachments/assets/8dab3c1c-3dc4-4dd1-9fc4-ea44fbaea734" align="right"/>

The CAD files for Microduck are in the `cad/` directory of this repository. It contains all the printable parts in both STL and STEP formats.

A visual representation of the 3D model can be found in the [Onshape assembly](https://cad.onshape.com/documents/d424992a192a8ce34ffce163/v/7de3e6e40f0e1185d169e6d9/e/b34620a03cc3a684006c5867?renderMode=0&uiState=6a2fccab8e6d9214d2644ca7). This interactive assembly allows you to explore the robot's design in detail, providing a better understanding of how the parts fit together. It also serves as a reference for assembly, helping you visualize the final product and ensuring that you can correctly identify each component during the build process.

An emphasis is placed on the range of motion of the 19 degrees of freedom of the robot. It allows for a wide variety of movements, making it suitable for various applications. Stops are integrated into the design to control which self-collisions are likely to occur, ensuring that the robot can move safely without damaging itself. The design also takes into account the cable routing for the servo motors, ensuring that the wires are neatly organized and do not interfere with the robot's movements.

---

## 🚀 Getting Started 

> **Need help during the build?** 
> If you run into any issues while sourcing components, printing parts, or assembling your Microduck, don't hesitate to ask the community in the **[Q&A Discussions section](https://github.com/Rhoban/microduck/discussions/categories/q-a)**!

To build your own Microduck, you will need to follow these steps:

1. **Source the hardware:** Gather the components listed in the [BOM](docs/bom.md). Links are provided to purchase each item, but feel free to source them from your preferred suppliers. Some components, like the Dynamixel motors, may have specific distributors depending on your location, which can impact the total cost. 

2. **Print the parts:** Head over to the `cad/stl/` folder and print all the parts using a 3D printer. The recommended filament is PLA with a layer height of 0.12mm and a 15% infill. Some parts require specific orientations for printing to ensure strength and proper fit. Refer to the [Printing Guide](docs/printing.md) for detailed instructions on how to print each part correctly.

3. **Assemble:** Follow our step-by-step [Assembly Guide](docs/assembly.md) to put the mechanics together.

4. **Deploy the software:** Once the robot is assembled, you can deploy the software on the Raspberry Pi Zero 2W by following the instructions in the [Deployment Guide](docs/deployment.md). 

5. **Drive it:** See the [Usage Guide](docs/usage.md) to run the robot, control it with the keyboard or a gamepad, and learn how to add your own moves.

---

## 🤝 Contributing

This project is community-driven! Whether it's designing a new head, writing code, or simply fixing typos in the documentation, contributions are always welcome. Feel free to fork the repository, make your changes, and submit a Pull Request. 

If you build your own Microduck, don't hesitate to share it in the **[Show and Tell section](https://github.com/Rhoban/microduck/discussions/categories/show-and-tell)**! 

If you just want to share ideas or chat about the project, you are also more than welcome to join the **[General Discussions](https://github.com/Rhoban/microduck/discussions/categories/general)**.

---

## 📄 License & Commercial Use

Copyright (c) 2026 Marc Duclusaud.

This project uses a dual-licensing model to keep the project open for the community while protecting the author's work from unauthorized commercial exploitation.

* **Hardware & Documentation (CAD, STL, Docs):** Licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
* **Software (Source Code):** Licensed under [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html).

To summarize the licenses:

* **Hobbyists, Makers & Researchers:** You are **100% free** to download, 3D-print, build, modify, and hack Microduck for your personal, educational, or academic research use. If you share your modifications, you must release them under the same licenses.
* **Commercial Entities & Companies:** You **cannot sell this robot**, sell parts/kits, or use this hardware/software design in commercial products without prior explicit written permission.

### ⚠️ Commercial Inquiries

If you wish to manufacture, distribute, or sell products based on Microduck (including selling pre-printed 3D parts, electronics kits, or fully assembled robots), you **must acquire a Commercial License**.

For licensing terms, commercial partnerships, or inquiries, please reach out to me on [LinkedIn](https://www.linkedin.com/in/marc-duclusaud/).

---

## 📚 Citation

If you use Microduck in your research, please cite it as follows:

```bibtex
@software{mduclusaud-microduck,
    author = {Duclusaud, Marc},
    doi = {10.5281/zenodo.20784789},
    month = jun,
    title = {{Microduck: A Compact, Fully 3D-Printable Open-Source Humanoid Robot}},
    url = {https://github.com/Rhoban/microduck},
    howpublished = "\url{https://github.com/Rhoban/microduck}",
    version = {1.0.0},
    year = {2026}
}
```

---

<p align="center">
  <img width="100%" alt="image" src="https://github.com/user-attachments/assets/f944db1b-b324-4915-a785-72229313eb72" />
</p>
  
