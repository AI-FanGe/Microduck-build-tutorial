# Printing Guide

This guide provides detailed instructions on how to print the parts for the Microduck robot. It covers recommended settings, orientations, and tips to ensure successful prints. To see the full assembly of the parts, you can refer to the [Onshape assembly](https://cad.onshape.com/documents/d424992a192a8ce34ffce163/v/7de3e6e40f0e1185d169e6d9/e/b34620a03cc3a684006c5867?renderMode=0&uiState=6a2fccab8e6d9214d2644ca7).


## Recommended Settings

The parts are available in the `cad/stl/` directory of this repository, and they are designed to be printed using a standard desktop 3D printer with PLA filament, 0.12mm layer height, and 15% infill. The next table summarizes the number of parts to print for each component of the robot. Please note that some parts may require specific orientations for printing, please refer to the [Part Orientation](#part-orientation) section for more details.

| Part | Quantity | Image | Description / Notes |
| :--- | :---: | :--- | :--- |
| foot.stl | 2 | <img width="971" height="874" alt="image" src="https://github.com/user-attachments/assets/d80a1d39-f88e-4849-9afc-7b9e5cfd26d4" /> | Feet of the robot. |
| tibia_left.stl | 1 | <img width="721" height="756" alt="image" src="https://github.com/user-attachments/assets/d6f858fb-4ae7-40c0-af1e-adee04824264" /> | Left tibia of the robot. Asymmetric to ensure proper cable routing. |
| tibia_right.stl | 1 | <img width="747" height="754" alt="image" src="https://github.com/user-attachments/assets/902565bc-84df-453a-bd6c-62ec0f6f840e" /> | Right tibia of the robot. Asymmetric to ensure proper cable routing. |
| femur_left.stl | 1 | <img width="491" height="796" alt="image" src="https://github.com/user-attachments/assets/af19700d-502d-405a-961e-97e5580db055" /> | Left femur of the robot. Asymmetric to ensure proper cable routing. |
| femur_right.stl | 1 | <img width="515" height="856" alt="image" src="https://github.com/user-attachments/assets/ab64844d-cb13-4d45-bf2e-cc5cbb3ce608" /> | Right femur of the robot. Asymmetric to ensure proper cable routing. |
| hip.stl | 2 | <img width="607" height="449" alt="image" src="https://github.com/user-attachments/assets/9102af47-c0c8-4f3b-a669-976ab60a1eb5" /> | Hips of the robot. |
| ankle_dbl_block.stl | 2 | <img width="869" height="602" alt="image" src="https://github.com/user-attachments/assets/0ca09907-a259-4bde-91cd-de54ca02d187" /> | Double motor blocks for the ankle joint. |
| hip_dbl_block_left.stl | 1 | <img width="898" height="630" alt="image" src="https://github.com/user-attachments/assets/7e6e471a-c734-44c6-b331-8d66b46b4c45" /> | Left double-motor block for the hip joint. Asymmetric to ensure proper cable routing. |
| hip_dbl_block_right.stl | 1 | <img width="950" height="670" alt="image" src="https://github.com/user-attachments/assets/6a4af16f-edb3-4eeb-a5a5-280c85958cf4" /> | Right double-motor block for the hip joint. Asymmetric to ensure proper cable routing. |
| spacer.stl | 4 | <img width="718" height="369" alt="image" src="https://github.com/user-attachments/assets/bf4c581b-8725-46f5-8d51-42a2b91a6824" /> | Cable clearance spacers for ankle and hip double-motor blocks. |
| pelvis.stl | 1 | <img width="1112" height="752" alt="image" src="https://github.com/user-attachments/assets/cc973f72-c75c-404e-a73a-09b3fb9888d8" /> | Pelvis of the robot. Lower part of the torso. |
| chest.stl | 1 | <img width="822" height="793" alt="image" src="https://github.com/user-attachments/assets/b99a47ed-a016-488a-b26b-bb87c385d71a" /> | Chest of the robot. Middle part of the torso. |
| trunk_top.stl | 1 | <img width="1021" height="571" alt="image" src="https://github.com/user-attachments/assets/77e01cfd-09ad-4ae0-bc44-6f1606261a30" /> | Top part of the torso. |
| head.stl | 1 | <img width="520" height="351" alt="image" src="https://github.com/user-attachments/assets/7c6244a3-d747-4c17-b2f6-2ca792bcd3e2" /> | The head of the robot. Currently just cosmetic, but can be modified to include sensors or cameras. |
| arm_bearing_support.stl | 2 | <img width="888" height="459" alt="image" src="https://github.com/user-attachments/assets/28cf9d96-4239-4e18-8e62-0b7f2690895a" /> | Supports for the shoulder shims. Printed separately from the chest to allow for better orientation and print quality. |
| shoulder.stl | 2 | <img width="533" height="457" alt="image" src="https://github.com/user-attachments/assets/755265fe-8790-48eb-b34c-a5c6f9dfb3e8" /> | Shoulder joints of the robot. |
| humerus.stl | 2 | <img width="741" height="575" alt="image" src="https://github.com/user-attachments/assets/eb17748b-e496-4ea1-b7d1-89c7314b1584" /> | Upper arms of the robot. |
| radius.stl | 2 | <img width="396" height="861" alt="image" src="https://github.com/user-attachments/assets/1a880519-1306-4f23-b5ab-d61efd1680c8" /> | Lower arms of the robot. |
| idle_horn.stl | 4 | <img width="1074" height="716" alt="image" src="https://github.com/user-attachments/assets/bc5c3803-9362-4e6c-a5a5-b7352a124a70" /> | Idle horn for XL330 motors. This part can be bought from Robotis, but printing it does not affect the quality and is cheaper. |
| idle_cap.stl | 6 | <img width="524" height="514" alt="image" src="https://github.com/user-attachments/assets/a3833483-3d2a-487b-b7ea-cfcec248ceff" /> | Idle cap to fit the idle horn. This part can be bought from Robotis, but printing it does not affect the quality and is cheaper. Two of the caps are designed to fit the forearm parts (radius). |
| board_spacer.stl | 4 | <img width="312" height="300" alt="image" src="https://github.com/user-attachments/assets/1adc94f8-83a2-4a12-8604-1ad90728207e" /> | Unthreaded spacer to place between the Raspberry Pi and the RPI Robot hat. | 


## Part Orientation 

The parts that support the plain bearings (POM washers sandwiched between steel shims) should be printed in a specific orientation to ensure proper fit and surface finish. These orientations can increase the required support material, but they are necessary to ensure that the bearings fit correctly and that the parts function as intended. These parts are: 
- `hip.stl`
- `pelvis.stl`  
- `arm_bearing_support.stl`
- `shoulder.stl`

The following parts also require specific orientations to ensure proper fit and alignment with the motors:
- `idle_horn.stl`
- `idle_cap.stl`
- `radius.stl`

The following images show the recommended orientations for the parts listed above.

<img width="100%" alt="image" src="https://github.com/user-attachments/assets/cfa211df-709d-4d61-a312-1d02fa6255d2" />

<br>
<br>

For all the other parts, the orientation is quite straightforward, and they can be printed without the need of support material for a lot of them.


---

Once you have all the parts, if you already purchased the necessary components listed in the [BOM](bom.md), you can proceed to assemble the robot by following the [Assembly Guide](assembly.md).
