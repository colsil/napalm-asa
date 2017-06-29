[![PyPI](https://img.shields.io/pypi/v/napalm-asa.svg)](https://pypi.python.org/pypi/napalm-asa)
[![PyPI](https://img.shields.io/pypi/dm/napalm-asa.svg)](https://pypi.python.org/pypi/napalm-asa)
[![Build Status](https://travis-ci.org/napalm-automation/napalm-asa.svg?branch=master)](https://travis-ci.org/napalm-automation/napalm-asa)
[![Coverage Status](https://coveralls.io/repos/github/napalm-automation/napalm-napalm-asa/badge.svg?branch=master)](https://coveralls.io/github/napalm-automation/napalm-napalm-asa)


# napalm-asa

A napalm project driver for the Cisco ASA


## Instructions


### The Tests

A Vagrantfile for a virtual machine running ASAv is provided but you'll need to have the VMWare desktop plugin for
 vagrant to run it, and to have the cisco-asav box available. Instructions for os/x are [here](http://binarynature.blogspot.co.uk/2016/07/cisco-asav-vagrant-box-for-vmware-fusion.html)

Code for testing is inside the `test` folder.

* `test/unit/TestDriver.py` - Here goes the following classes:
  * `TestConfigDriver` - Tests for configuration management related methods.
  * `TestGetterDriver` - Tests for getters.
  * `FakeDevice` - Test double for your device.
* `test/unit/skeleton/` - Here goes some configuration files that are used by `TestConfigDriver`.
* `test/unit/skeleton/mock_data/` - Here goes files that contain mocked data used by
                                    `TestGetterDriver`.

#### Testing getters

This is easier, we can use a real machine or just mock the device. Write a test double for your
device and provide the necessary mocked data.

### Other files
