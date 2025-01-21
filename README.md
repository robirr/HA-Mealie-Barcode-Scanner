# Home Assistant (and Mealie) Barcode Scanner and Product Lookup

[![GitHub license](https://img.shields.io/github/license/MattFryer/HA-Mealie-Barcode-Scanner.svg?logo=gnu&logoColor=ffffff)](https://github.com/MattFryer/HA-Mealie-Barcode-Scanner/blob/master/LICENSE)
![GitHub commit activity](https://img.shields.io/github/commit-activity/t/MattFryer/HA-Mealie-Barcode-Scanner)
![GitHub contributors](https://img.shields.io/github/contributors/MattFryer/HA-Mealie-Barcode-Scanner)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/MattFryer/HA-Mealie-Barcode-Scanner)
![GitHub Repo stars](https://img.shields.io/github/stars/MattFryer/HA-Mealie-Barcode-Scanner)
![GitHub forks](https://img.shields.io/github/forks/MattFryer/HA-Mealie-Barcode-Scanner)
![GitHub watchers](https://img.shields.io/github/watchers/MattFryer/HA-Mealie-Barcode-Scanner)


[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/mattfryer)
![GitHub Sponsor](https://img.shields.io/github/sponsors/MattFryer?label=Sponsor&logo=GitHub)

Being big users of both Home Assistant and Mealie, for a while I've looked for a solution to add items quickly to our Mealie shopping list by scanning the product barcode. I’ve seen lots of questions about the same idea on the HA community and Reddit, but haven’t seen any great solutions. So I set about making my own solution. The code for which and my notes as I develop the solution can be found in this repository.

> [!IMPORTANT]
> This project is a work in progress and is currently no more than a Proof Of Concept (PoC). Therefore it is subject to change and the code and examples in this repository may not work. The below is not an exhaustive walkthrough and so a reasonable understanding of Home Assistant and ESPHome will be needed to successfully follow and implement.

> [!WARNING]
> No warranties or guarantees are made regarding the contents of this repository. Anyone using the code or instructions does so at their own risk!

## The Idea
The main idea is to have a way to scan a product barcode whilst preparing a meal in the kitchen and have that item added to the weekly supermarket shopping list. To ensure it is used by the whole family, it needs to be fast and simple to scan a barcode whilst preparing a meal. Ideally it will use a device mounted in the kitchen so that it doesn't require a mobile phone to work. 

Once a barcode is scanned, it will need to be converted to a product name and then added to the shopping list. This could be any To-Do list in Home Assistant, including one created and synched by the Mealie integration. It will need to a method to highlight when a product name can't be found and to prompt the user to add the product name manually. This should be store for future lookup.

## The Solution
The planned solution is made up of 3 main parts: 
1. A hardware solution to scan the product barcode and pass it to Home Assistant. This is powered using ESPHome of speed of implementing and ease of integrations.
2. A Python script running in the Pyscripts integration in Home Assistant which looks up a barcode on the UPCDatabase.org and/or OpenFoodFacts.org API and returns the product name.
3. A Home Assistant Automation to link the above together, triggering when a barcode is scanned, passing it to the Python script to get the name and then adding it to the desired shopping list.

### The Hardware

For simplicity of creation and integration with Home Assistant, prototype hardware has been created using [ESPHome](https://esphome.io/). The final hardware solution will likely also use ESPHome. If it is ever productionised, ESPHome can also be used with ability to register a product for automatic updates, etc. 

#### Parts

The minimum required hardware would be:
- An ESP8266 or ESP32 development board which can be brought widely on ebay or Aliexpress for under £5 (GBP). (e.g. [https://www.ebay.co.uk/itm/166478265403](https://www.ebay.co.uk/itm/166478265403))
- A suitable barcode scanner such as GM67 which can be brought widely on ebay and Aliexpress for around £20 (GBP). (e.g. [https://www.ebay.co.uk/itm/365225165259](https://www.ebay.co.uk/itm/365225165259))

![Prototype device](assets/images/prototype_gm67.png)

Optionally, you could also add a screen or LEDs to indicate if a scanned product was successfully identified. You could also add buttons to switch the scanner on and off or even to change which list you would like the product adding to. I might add these features to my eventual solution. 

#### Wiring
We need to wire the GM67 to the ESP board. Which pins on the ESP board you choose to use is up to you but your ESPhome YAML needs to match the pins. The below table shows the wiring colours and pins for the example ESPHome YAML files.

> [!CAUTION]
> The wiring colours of the cable provided with the GM67 are not standard. Care should be taken to ensure the correct wiring in order to not damage either the GM67 or the ESP board. Do not rely on the wiring colours as the cable provided may not be the same as the one I received.

| GM67 Board UART/TTL Pin | ESP Board Pin | Supplied Wire Colour |
| ----------------------- | ------------- | -------------------- |
| GND                     | GND           | Green                |
| RX                      | GPIO13        | Yellow               |
| TX                      | GPIO15        | Black                |
| 5V                      | 5V            | Red                  |

The cable provided for UART/TTL with the GM67 had bare wires to which I added Dupont connectors to make it simple to connect to the ESP board. You can connect however you wish (e.g. soldering). 

#### GM67 Configuration
Out of the box, the GM67 I received was configured to only talk on the USB interface. Unless this is changed, it won't interface and send barcodes to the ESP board. To change settings on the GM67 there is an extensive document containing special QR codes to apply settings. The documentation for all of the GM range of barcode scanners can be found [HERE](https://www.dropbox.com/scl/fo/87hz5h82k25j3p9k5u603/AJfkL6iYDATRGkLYJjuhUJE?rlkey=2fyvdir15kb1kj2ada1zkadqt&e=1&dl=0).

Assuming you have the GM67 like I do, you can scan the following QR code with the scanner to enable UART/TTL mode:

![TTL 232 Interface QR Code](assets/images/ttl232_enable.png)

Other configuration options for the GM67 are available from within Home Assistant once the ESPHome device has been configured.

So far, the GM67 has been very fast, accurate and reliable. 

> [!TIP]
> The GM67 seems to be good at reading codes from screens also and so you can open this page on your phone to be able to scan the above codes easily. 

#### ESPHome YAML
An example ESPHome YAML configuration file can be found in this repository under [/esphome/example-esphome-gm67.yaml](esphome/example-esphome-gm67.yaml). Some of the sensors created in the example are disabled in HA by default but can be enabled to help with debugging. 

A number of configuration options for the GM67 are also contained within the example YAML file. These settings can be used to tailor the GM67's behaviour as follows:
- Buzzer Volume: Sets the volume of the beep emitted when a barcode is scanned.
- Trigger Mode: Allows you to set the trigger mode which starts the GM67 scanning. The main options are: 
  - "Continuous Scanning" - which does exactly what it says and sets the GM67 to contiuously attempt to scan a barcode.
  - "Automatic Induction" - which turns on the scanning only when the light level in front of the scanner changes (e.g. when a product is placed in front) and turns off again after a short duration or if a barcode is scanned. This mode prevents the continuous red and white scanning lights from being on constantly.

<!-- Add all the configuration options in the example ESPHome file and describe the settings -->

> [!TIP]
> If you have any issues creating the hardware, you can try adding the following to your ESPHome YAML configuration:
> ```
> logger:
>   level: VERBOSE
> ```
> This will enable more detailed debug logging which should include all UART messages coming from the barcode scanner. This can help to prove the ESP and scanner are communicating correctly.

I may add more to the above example over time or add additional examples.

#### Home Assistant Device Config
The new device should show up in HA called "barcode-scanner" unless you changed it in the ESPHome YAML. Add it to Home Assistant as you would any other ESPHome device (it should be automatically found by HA). 

> [!IMPORTANT]
> If you do not perform the next steps, the ESPHome device will not be able to trigger events on the Home Assistant event bus which are needed to trigger the Home Assistant Automation later.

Follow the below steps to allow the device to trigger events on the HA event bus:
1. Open the ESPHome integration page on your Home Assistant instance:
    
    [![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=esphome)
2. Find your barcode scanning device in the device list.
3. Click the “CONFIGURE” button next to it.
4. Check the “Allow the device to perform Home Assistant actions” box.
5. Then click “submit”.

You can now check the device is working and connected to Home Assistant correctly:
1. Navigate to Developer Tools -> Events
2. Under "Listen to events" enter "esphome.barcode_scan"
3. Click "Start listening"
4. Scan a barcode with the device and you should see an event appear containing a line beginning "barcode:" followed by the barcode you scanned. Something like the below:
    ```
    event_type: esphome.barcode_scan
    data:
      device_id: ee685dc4d9ccb1de6e97a84beb7be650
      barcode: 4088600550862
    origin: LOCAL
    time_fired: "2025-01-20T12:54:21.634458+00:00"
    context:
      id: 01JJ1WEGP22MANX2VFREP5B2JV
      parent_id: null
      user_id: null
    ```

> [!IMPORTANT]
> Ensure you have the above working and can see the "barcode_scan" events in Home Assistant before moving on.

### Product Lookup
A custom python script is used to look up a passed product barcode on the [openfoodfacts.org](https://openfoodfacts.org/) website and return the name of the product. Home Assistant can run custom python scripts directly but additional python libraries can't be important which limits what can be done with them.

Instead, we can use the [Pyscript](https://github.com/custom-components/Pyscript) integration to run out python script. 

#### Install the Pyscript Integration in HA
If you aren't already using Pyscripts for some other purpose then you need to install it. Full instructions for how to install the Pyscript integration can be found on the repository [https://github.com/custom-components/Pyscript](https://github.com/custom-components/Pyscript). 

Pyscript can be easily installed via the Home Assistant Community Store (HACS). Assuming you have HACS installed within your HA instance already, simply search for "Pyscript" within HACS (or click on the below button), and then install it. 

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=pyscript&owner=custom-components)

Once installed, you need to add the integration under the integrations section of Home Assistant. You can do this manually or you can click the below button:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=pyscript).

> [!IMPORTANT]
> Make sure to check the option for "Allow All Imports?" when adding the Pyscript integration. If you do not, our python script will not be able to load the needed python modules. Don't worry if you missed it or already have Pyscripts installed, you can check and set this option by going to the Pyscript integration page and clicking on "CONFIGURE".

#### Add the python script under Pyscripts
Pyscript can have a bit of a learning curve to set up and the documentation isn't be best for beginners. Don't worry thought, if this is the first time you are using Pyscript in your HA instance, you can simply copy the "pyscript" folder and all of its contents and subfolders from this repository to your Home Assistant config folder. 

If you already had Pyscript installed and running other python scripts, you should hopefully already understand the basics of how Pyscript is configured. You will need to copy the "pyscript/apps/barcode_lookup" folder and its contents from this repository under your existing "pyscript/apps" folder (or create one) in your Home Assistant config folder. You will also need to amend your "pyscript/config.yaml" file to include the definition and settings for this new Pyscript app. You can copy them from the ["pyscript/config.yaml"](pyscript/config.yaml) file in this repository.

> [!TIP]
> Pyscript should pick up the new script automatically but to be sure it is best to restart Home Assistant to make sure everything is reloaded.

The Pyscript app configuration contains the base path to use for the OpenFoodFacts.org API. This is so that it is easy to amend in the future if needed without having to modify the python script (i.e. if they move from v2 to v3 of their API).

If the Pyscript app has been installed and configured correctly, you should be able to test calling the created service from within Home Assistant:
1. Navigate to Developer Tools -> Actions
2. Find and select the "Pyscript Python scripting: Barcode Lookup" action.
3. Click the "FILL EXAMPLE DATA" link from under the "All available parameters" section which should configure the action with the barcode "5000147030156".
4. Click on "PERFORM ACTION"
5. If all is configured and working properly you should see a returned response which looks like this:
    ```
    result: success
    barcode: 5000147030156
    brand: Robinsons
    title: Summer Fruits Squash
    type: food
    quantity: ""
    ```

As you can see, the returned data contains a number of fields from the OpenFoodFacts API witch you can use as conditions in automations. For example, you could use the "result" to only add the product to the shopping list if a successful match is found. Or you could add the product to a different shopping list if the "type" isn't food.

> [!IMPORTANT]
> Ensure you have the above working and you can call the service and get a success response before moving on.

> [!TIP]
> If you have issues, you can enable verbose logging for Pyscript by adding the below to your Home Assistant configuration.yaml:
>   ```
>   logger:  
>     custom_components.pyscript: info
>   ```
> You should then be able to see detailed logging including any errors in the Home Assistant logs.

### Home Assistant Automation
[Coming Soon]
<!-- Need to change current automation to trigger on the HA event "esphome.scanned_barcode" and upload an example yaml -->

## Planned Improvements / To Investigate
- [X] Switch to using openfoodfacts.org instead as seems better populated.
- [ ] If the product isn't found on openfoodfacts.org then try upcdatabase.org instead. Possible other sources of product lookup also.
- [ ] Implement a local cache of barcodes and their product names to prevent hitting the APIs unnecessarily and also to allow adding custom matches to override or for unknown products.
- [ ] If a product isn't found, HA could send a notification asking for you to input the product name. It can then be added to the cache. Could even send to whoever is in the kitchen using presence detection. Or even ask using a voice assistant?
- [ ] Consider implementing the automation and python as a HA integration for easier set up. Might be less flexible though.
- [ ] A screen for feedback of if the scanned code was found and buttons to change which shopping list you want the product added to.
- [ ] Investigate if a scanned product can be found on Amazon and added to your shopping basket ready for purchase.
- [X] Investigate sending serial commands to the GM67 to allow for options in the HA device to configure the scanning mode, to turn off the scanner, etc. 
- [ ] Option to have special QR codes which when scanned add some text in the QR code to the list rather than doing a barcode lookup (e.g. Add "Milk" to the shopping list). Possible to trigger a different HA event if the scanned code starts with a specific string.
- [ ] 3D printable case to house the parts under a kitchen cupboard with the barcode scanner facing down. Straight down or angled?
- [ ] Better detecting of a product in front of the scanner using a time of flight sensor.