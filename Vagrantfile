# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.ssh.insert_key = false
  config.vm.box = "cisco-asav"
  # Shorten timeout value for lack of "standard" Cisco ASA shell
  config.vm.boot_timeout = 90
  # Disable default host <-> guest synced folder
  config.vm.synced_folder ".", "/vagrant", disabled: true

  # Modify telnet port number for console OOB management
  config.vm.provider "vmware_fusion" do |v|
    v.vmx["serial0.fileName"] = "telnet://127.0.0.1:52001"
  end
end