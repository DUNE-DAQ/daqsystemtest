### HD Coldbox Configs

Run these commands to generate the configs:

```
daqconf_multiru_gen --enable-dqm -c np04_coldbox_daq_4ms.json --hardware-map-file <full/path/to>/Hardware_HDColdbox.txt np04_coldbox_daq_4ms

wibconf_gen -c np04_coldbox_wibs_2us.json np04_coldbox_wibs_2us

felixcardcontrollerconf_gen.py -c np04_coldbox_flx_ctrl.json --hardware-map-file <full/path/to>/HardwareMap_HDColdbox.txt np04_coldbox_flx_ctrl

```

you'll then want a global config file to give to `nano04rc` that looks like:
```
{
    "apparatus_id":"np04_coldbox",
    "np04_coldbox_wibs":"np04_coldbox_wibs_2us",
    "np04_coldbox_felix_ctrl":"np04_coldbox_flx_ctrl",
    "np04_coldbox_daq":"np04_coldbox_daq_4ms"
}
```

Check to make sure that the `output_paths` is set as you like in `np04_coldbox_daq_4ms.json`, and that location to hardware map files and cpu pinning files (in `readout` in `np04_coldbox_daq_4ms.json`) is correct.