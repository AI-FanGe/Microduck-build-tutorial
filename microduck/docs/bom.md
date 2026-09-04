# Bill of Materials (BOM)

Here is a detailed Bill of Materials (BOM) for the project, including links to purchase each component and their approximate prices. Please note that prices may vary based on location and availability. You can source the components from your preferred suppliers, but beware that for electronic components using cheaper distributors may result in lower quality and reliability. 

Unlike the other components, the **[RPI Robot Hat](https://github.com/pollen-robotics/elec_RPI_Robot_HAT)** is not an off-the-shelf part: it is an open-source board that you need to have manufactured. Its design files are freely available on GitHub and can be ordered from any PCB fabrication service (e.g. JLCPCB, PCBWay, Aisler). The listed price is a rough estimate and will depend on the fab you choose and the quantity ordered. 

At the time of writing, **a Microduck robot costs approximately $567**.

If you also include the configuration tools (Dynamixel U2D2 and U2D2 Power Hub), the total cost rises to approximately $623.


## Robot Components

To build a complete Microduck robot, you will need the following components:

| Component | Image | Quantity | Price | Link | Description / Notes |
| :--- | :---: | :---: | :--- | :--- | :--- |
| Battery Holder | <img width="495" height="370" alt="image" src="https://github.com/user-attachments/assets/c34fd978-c4ad-4e65-9ab5-c66cf8f0093d" /> | 1 | ~$5.00 | [Amazon](https://www.amazon.fr/gp/product/B08YDTSML8/ref=sw_img_1?smid=A9DEKVHK1XMRT&th=1) | 2x18650 Battery Holder. |
| BMS | <img width="578" height="334" alt="image" src="https://github.com/user-attachments/assets/6e34f026-2986-484f-9baa-1df57be5c0dd" /> | 1 | ~$10.00 | [Amazon](https://www.amazon.fr/gp/product/B0GJLGG7MM/ref=ewc_pr_img_1?smid=A263J3XHEW00G8&psc=1) | Battery Management System for 2x18650 batteries. |
| Switch | <img width="227" height="165" alt="image" src="https://github.com/user-attachments/assets/269e7adf-49be-4885-bb97-f27f1dc2e84b" /> | 1 | ~$5.00 | [Amazon](https://www.amazon.fr/gp/product/B0F32NVDHW/ref=ewc_pr_img_1?smid=A3PA4HG72LIUMJ&psc=1) | Power switch for the robot. |
| Charger | <img width="517" height="355" alt="image" src="https://github.com/user-attachments/assets/7c87ae54-b69d-45ce-b1f4-3c94d7554002" /> | 1 | ~$10.00 | [Amazon](https://www.amazon.fr/gp/product/B0BWTK7SVN/ref=ox_sc_act_title_1?smid=A25R4KS2AL1P7J&psc=1) | Standard USB-C charger. |
| Batteries | <img width="291" height="119" alt="image" src="https://github.com/user-attachments/assets/01e57659-3c0d-4490-8d46-2c5ae151940b" /> | 2 | ~$4.00 each | [Nkon](https://www.nkon.nl/fr/sony-murata-us18650-vtc6.html) | 18650 3.7V Lithium-ion Batteries. Murata VTC6 are recommended but not mandatory. |
| Raspberry Pi Zero 2W | <img width="515" height="353" alt="image" src="https://github.com/user-attachments/assets/8d1380e7-ee46-45aa-ac96-b55b4dadb0cb" /> | 1 | ~$15.00 | [Raspberry Pi](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) | Microcontroller for the robot. |
| RPI Robot Hat | <img width="1274" height="871" alt="image" src="https://github.com/user-attachments/assets/0a297b9a-a445-46f9-9fb0-f91548307426" /> | 1 | ~$30.00 | [GitHub](https://github.com/pollen-robotics/elec_RPI_Robot_HAT) | Open-source custom hat for the Raspberry Pi Zero 2W. The design files are available on GitHub and can be manufactured by any PCB fabrication service. |
| 16GB+ micro SD card | <img width="246" height="183" alt="image" src="https://github.com/user-attachments/assets/7a2fe517-e3e7-47b6-9966-2838ed620ccf" /> | 1 | ~$10.00 | [Amazon](https://www.amazon.fr/-/en/SanDisk-microSDHC-Adapter-Performance-SDSQUA4-032G-GN6MA/dp/B08GY9NYRM/ref=sr_1_17?crid=O5SONJ8M41FU&dib=eyJ2IjoiMSJ9.N0O0ZyTK7SFmwPAxWOn5oeL2zSZluRXIFYtW-yyCkbLOIGtmYKqAPjoPCPBBKT2SqTnXVN_WUlEtRtDlz-_T8GwlCS5fb_56nVvy2k3sVqmcfNSx8D4P8ZLnG2v_-ijJd2iwtGph-uaNffLic3eoBQ-Ks1PzmkL-A2pBKleoOFnBmbfTwADpYnJ78lN066Tm-P0Lo1Z5oZEfncC1pAX_077dIlD8jRriZXfAj4hwWTt8YUl7D5ZjTC2Y_SjsMnUKdIgrt7p4KVKrUfQaPdknL6krTdBaYQlN0Hofl_miVUA.qN2mUVBbFdJp9tIHCuN-ttjj-TfpmDhS2Erb25sFB-I&dib_tag=se&keywords=sandisk%2BA1%2B16gb%2Bmicro%2Bsd&qid=1781699284&s=computers&sprefix=sandisk%2Ba1%2B16gb%2Bmicro%2Bs%2Ccomputers%2C141&sr=1-17&th=1) | Class 10 micro SD card of at least 16GB for OS and software. |
| Dynamixel XL330-M288-T | <img width="241" height="288" alt="image" src="https://github.com/user-attachments/assets/703ab319-5651-41da-a37b-81ff1c046413" /> | 19 | $23.90 each | [Robotis](https://en.robotis.com/shop_en/item.php?it_id=902-0163-000) | Servomotor with 1 motor, 1 180mm cable, 10 2.2x8 screws, 6 2x6 screws. |
| M2x6 STP39 Screws | <img width="248" height="153" alt="image" src="https://github.com/user-attachments/assets/26d87e70-0839-470f-9a63-286f6c794f57" /> | 10 | ~$3 (depends on quantity) | [Screwerk](https://de.screwerk.com/fr/shop/detail/stp/STP390200060S.html) | Screws for the motor horns. Self-tapping screws for plastic. Complete the screws from motor kits. |
| Filament material | <img width="446" height="448" alt="image" src="https://github.com/user-attachments/assets/7ce91362-f8da-449e-b582-aaa9d4ea19f4" /> | <1 | ~$10.00 | Depends on the 3D printer | To print the robot parts. Less than one roll. |
| 20x30x1mm POM shims | <img width="1427" height="901" alt="image" src="https://github.com/user-attachments/assets/0b479c24-fd4b-4815-963c-a803d76a7457" /> | 4 | ~$2.50 for 20 | [AliExpress](https://fr.aliexpress.com/item/1005006482475865.html?spm=a2g0o.order_list.order_list_main.9.76795e5b3T2may&gatewayAdapt=glo2fra) | POM washers used as plain bearings. Alternative to needle bearings for motors without idler horns. |
| 25x30x0.3mm Steel shims | <img width="987" height="844" alt="image" src="https://github.com/user-attachments/assets/7bd4f1a3-2d4f-4b8d-ae9c-7e6806afd1e5" /> | 8 | ~$1.75 for 10 | [AliExpress](https://fr.aliexpress.com/item/1005001878233881.html?spm=a2g0o.order_list.order_list_main.4.71cd5e5bu57Z22&gatewayAdapt=glo2fra) | Parts on which the POM shim rests. |
| M2.5x6 Screws | <img width="255" height="171" alt="image" src="https://github.com/user-attachments/assets/6e67770b-e629-4bf0-bc25-4675397e4f56" /> | 18 | ~$3 (depends on quantity) | [Screwerk](https://de.screwerk.com/fr/shop/detail/stm/STM320200060S.html) | Standard M2.5x6 screws to attach the idle horns to the motors. Any standard should work. |

**Important Note:** The total number of M2x6 screws contained in 19 motor kits is 114, while the number of M2x6 screws required for the assembly is 124. If you buy more than 19 motors, you will have enough screws for the assembly. If you buy exactly 19 motors, you will need to buy 10 additional M2x6 screws. I personally recommend buying some additional M2x6 screws to avoid any issues during assembly. I also recommend buying M2.2x8 for the motor fixation, as the M2x8 screws provided with the motors may not fit perfectly, although they are usable. Check the [Optional Components](#optional-components) section for more details.


## Configuration Tools

In addition to the components that make up the robot, you will also need configuration tools to set up the Dynamixel motors:

| Component | Quantity | Price | Link | Description / Notes |
| :--- | :---: | :--- | :--- | :--- |
| Dynamixel U2D2 | 1 | $32.10 | [Robotis](https://en.robotis.com/shop_en/item.php?it_id=902-0132-000) | USB to Dynamixel adapter for motor configuration. |
| Dynamixel U2D2 Power Hub | 1 | $19.00 | [Robotis](https://en.robotis.com/shop_en/item.php?it_id=902-0145-001) | Power hub for U2D2. |
| 5V DC Power Supply | 1 | ~$5.00 | [AliExpress](https://fr.aliexpress.com/item/1005006681380264.html?src=google&src=google&albch=shopping&acnt=248-630-5778&isdl=y&slnk=&plac=&mtctp=&albbt=Google_7_shopping&aff_platform=google&aff_short_key=UneMJZVf&gclsrc=aw.ds&albagn=888888&ds_e_adid=&ds_e_matchtype=&ds_e_device=c&ds_e_network=x&ds_e_product_group_id=&ds_e_product_id=fr1005006681380264&ds_e_product_merchant_id=109233876&ds_e_product_country=FR&ds_e_product_language=fr&ds_e_product_channel=online&ds_e_product_store_id=&ds_url_v=2&albcp=19000710609&albag=&isSmbAutoCall=false&needSmbHouyi=false&gad_source=1&gad_campaignid=17725339642&gbraid=0AAAAACWaBweuoiaNc4XiSTkGHPjyMW6GD&gclid=Cj0KCQjwrs7RBhDuARIsAIVfBD0W5aMl1lU2v3nhWRxGFVcibpgHUv8IFQLeOQACU-XE4MzK3mm_oPoaArMQEALw_wcB) | 5V DC power supply for U2D2 Power Hub. Does not require a lot of current, it is only needed for the initial configuration. |

In case of building several robots, it is not necessary to buy several U2D2 sets, as they are only required for the initial configuration of the motors. 


## Optional Components

As discussed in the [Robot Components](#robot-components) section, I personally recommend replacing the provided M2x8 screws by M2.2x8 screws. For your information, the total amount of M2x6 self-tapping screws required for the assembly is 124, they are used to fix the horns to the parts. The total amount of M2x8 / M2.2x8 self-tapping screws required for the assembly is 66, they are used to fix the motors to the parts. Having extra screws can also be useful in case of loss.

The number of cables provided with the motors should be sufficient for the robot, but you may need additional cables in case of damage. 
It is also preferable to adjust the cable lengths to the minimum required for the robot to avoid cable entanglement. It is possible to only use off-the-shelf cables of size 50mm (6), 100mm (4), and 180mm (9), but due to the lack of availability, it is preferable to crimp your own cables. To do so, you can buy SEH-001T-P0.6 crimp pins and adjust 180mm cables to the required lengths. Detailed instructions on how to crimp your own cables will be provided in the Assembly Guide.

Finally, if you plan to use Microduck intensively, you may want to consider having additional batteries and a charger to avoid downtime during charging. 

For all these reasons, here are some optional components you may want to consider:

| Component | Quantity | Price | Link | Description / Notes |
| :--- | :---: | :--- | :--- | :--- |
| Screws STP39 2x6 | 100 | ~$30 (depends on quantity) | [Screwerk](https://de.screwerk.com/fr/shop/detail/stp/STP390200060S.html) | Optional self-tapping screws for horn to part attachment. |
| Screws STP39 2.2x8 | 100 | ~$30 (depends on quantity) | [Screwerk](https://de.screwerk.com/fr/shop/detail/stp/STP390220080B.html) | Optional screws self-tapping for motor to part attachment. |
| Additional cables | 10 | $19.00 | [Robotis](https://en.robotis.com/shop_en/item.php?it_id=903-0249-000) | X3P cables for motors. Can be made with JST EHR-3 connectors. |
| SEH-001T-P0.6 | 100 | ~$5 | [AliExpress](https://fr.aliexpress.com/item/1005005433081646.html?spm=a2g0o.productlist.main.14.4cb73Yt63Yt6Kq&algo_pvid=2d88a1fc-538c-419c-b979-d824664a9d61&algo_exp_id=2d88a1fc-538c-419c-b979-d824664a9d61-13&pdp_ext_f=%7B%22order%22%3A%227%22%2C%22eval%22%3A%221%22%2C%22fromPage%22%3A%22search%22%7D&pdp_npi=6%40dis%21USD%215.48%215.48%21%21%2136.86%2136.86%21%40211b653717817828771658630e4999%2112000033054910532%21sea%21FR%214783434133%21X%211%210%21n_tag%3A-29919%3Bd%3Ac460c166%3Bm03_new_user%3A-29895&curPageLogUid=F1bvVQoND3ep&utparam-url=scene%3Asearch%7Cquery_from%3A%7Cx_object_id%3A1005005433081646%7C_p_origin_prod%3A) | JST EH crimp pin of size 2.50mm in roll. Compatible with JST EHR-3 connectors. |
| Crimp tool | 1 | ~$12 | [AliExpress](https://fr.aliexpress.com/item/1005003429462091.html?spm=a2g0o.detail.pcDetailTopMoreOtherSeller.2.62b7kIjYkIjYQm&gps-id=pcDetailTopMoreOtherSeller&scm=1007.40050.354490.0&scm_id=1007.40050.354490.0&scm-url=1007.40050.354490.0&pvid=415cdc12-f8ef-42b1-82d4-be2f1c6965bd&_t=gps-id%3ApcDetailTopMoreOtherSeller%2Cscm-url%3A1007.40050.354490.0%2Cpvid%3A415cdc12-f8ef-42b1-82d4-be2f1c6965bd%2Ctpp_buckets%3A668%232846%238111%231996&pdp_ext_f=%7B%22order%22%3A%221126%22%2C%22eval%22%3A%221%22%2C%22sceneId%22%3A%2230050%22%2C%22fromPage%22%3A%22recommend%22%7D&pdp_npi=6%40dis%21USD%2112.82%2112.82%21%21%2112.82%2112.82%21%40210389a017817831629464610e0f28%2112000025744698739%21rec%21FR%214783434133%21X%211%210%21n_tag%3A-29919%3Bd%3Ac460c166%3Bm03_new_user%3A-29895&utparam-url=scene%3ApcDetailTopMoreOtherSeller%7Cquery_from%3A%7Cx_object_id%3A1005003429462091%7C_p_origin_prod%3A) | Crimping tool. Should contain a 1.9mm die for the SEH-001T-P0.6 crimp pin. |
| Additional batteries | 1 | ~$4 | [Nkon](https://www.nkon.nl/fr/sony-murata-us18650-vtc6.html) | 18650 3.7V Lithium-ion Batteries. Murata VTC6 are recommended but not mandatory. |
| 18650 Li-ion charger | 1 | ~$15 | [RS](https://fr.rs-online.com/web/p/chargeurs-de-batterie/1466770?cm_mmc=FR-PLA-DS3A-_-google-_-CSS_FR_FR_PMAX_Catch+All-_--_-1466770&matchtype=&&gclsrc=aw.ds&gad_source=1&gad_campaignid=20578377983&gbraid=0AAAAADkeWNPDTNsDLcd_uPpNf5dyuURwZ&gclid=Cj0KCQjwrs7RBhDuARIsAIVfBD1mWWQaUqq57uY0HczXxqt7IdnTHdIH2SJAiRoJVK7CXJE3iV0SwDAaAuRlEALw_wcB) | Charger for 18650 Li-ion batteries. |


---

Once you have all the components, you can proceed to print the parts. Follow the [Printing Guide](printing.md) for detailed instructions.

If you already have the parts printed and the components purchased, you can directly proceed to the assembly of the robot by following the [Assembly Guide](assembly.md).
