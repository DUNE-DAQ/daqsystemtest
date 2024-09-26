* 19-Jul-2023, ELF, KAB, and others: notes on existing integtests

"integtests" are intended to be automated integration and/or system tests that make use of the
"pytest" framework to validate the operation of the DAQ system in various scenarios.

Here is a sample command for invoking a test (feel free to keep or drop the options in brackets, as you prefer):

```
pytest -s minimal_system_quick_test.py [--nanorc-option log-level debug]  # still useful even with drunc
```

For reference, here are the ideas behind the tests that currently exist in this repository:
* `minimal_system_quick_test.py` - verify that a small emulator system works and successfully writes data in a short run
* `readout_type_scan.py` - verify that we can write different types of data (WIBEth, PDS, TPG, etc.)
* `3ru_3df_multirun_test.py` - verify that a system with multiple RUs and multiple DF Apps works as expected, including TPG
* `fake_data_producer_test.py` - verify that the FakeDataProdModule DAQModule works as expected
* `long_window_readout_test.py` - verify that readout windows that require TriggerRecords to be split into multiple sequences works as expected
* `3ru_1df_multirun_test.py` - verify that we don't get empty fragments at end run
  * this test is also useful in looking into high-CPU-usage scenarios because it uses 3 data producers in 3 RUs
* `tpstream_writing_test.py` - verify that TPSets are written to the TP-stream file(s)
