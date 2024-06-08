# jetson-nano-stuff
Everything to get the old Jetson Nano Developer Kit 2GB up and running with Ubuntu 20.04 and a lot of other things.

This guide refers to: https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-2gb-devkit This board is no longer in production as of 2024 but if you still have one (or more) of these and you want to play around with it, here's how I'd do it.

### 1) Intro - The board, drivers, CUDA and Ubuntu

1. This board is centered around the Tegra SoC that includes the processor (an early ARM v8 so yes, no SVE instructions, etc) and the GPU which is a nice 128 cores Maxwell device with compute capability 5.3. The GPU is technically an iGPU (integrated) and as such it is not a discrete device attached to the pci-e bus. This is a crucial point since the "discrete" nvidia drivers <b>won't work</b> with this gpu, even if the architecture is exactly the same to that of a discrete Maxwell gpu.
The only drivers that will work are those provided by nVidia in their "Linux 4 Tegra" (<b>L4T</b>) flavour of the Linux kernel. Since the driver version and the CUDA version must exactly match, no CUDA greater than 10.2 is supported on these devices. While the Maxwell architecture can run much higher CUDA versions, because of the gpu being integrated and the drivers being built-in in the L4T kernel, unless nvidia releases a new kernel with updated drivers, it is not possible to run CUDA beyond 10.2 (if one attempts to use a version > 10.2, the iGPU will fail to initialize and will result in random crashes).

2. The board also does not have a BIOS/EFI chip, but it uses a special partition on the SD card (more on this later on) in order to boot the device (other jetson nano's with different SoC have instead a flash chip where the bios/efi subsystem resides, this is not the case with the 2GB developer's version).

3. With respect to the OS, nvidia officially supports only Ubuntu 18. While it is not necessary, it can be updated to Ubuntu 20.04 to gain updated versions of some system libraries that are quite useful for a variety of tasks. The procedure to update the os is described later.

### 2) Creating a bootable SD card and first boot

The ideal minimum would be a <b>64 GB</b> card, class 10, so that you can enjoy great performance from the system. A 32 GB could work too but you'd only have a little more of 1 GB of usable space and this would not allow to allocate enough space for a swap file. The 2 GB of onboard memory + the default 1 GB swap is enough for most task but the memory gets quickly eaten away if you have to compile libraries and you'll need at least another 8 GB of swap file (assuming of course you use only 1 core during the compilation).

1. Do a <b>low level format</b> of the sd card, without a filesystem. This is important, otherwise the system won't boot or, in case it does, it could be unstable.

2. Go [here](https://developer.nvidia.com/embedded/linux-tegra-r3274) and download:
   1. The [driver package (BSP)](https://developer.nvidia.com/downloads/embedded/l4t/r32_release_v7.4/t210/jetson-210_linux_r32.7.4_aarch64.tbz2) which is actually the Linux 4 Tegra.
   2. The [sample root filesystem](https://developer.nvidia.com/downloads/embedded/l4t/r32_release_v7.4/t210/tegra_linux_sample-root-filesystem_r32.7.4_aarch64.tbz2) which is Ubuntu 18.
4. Prepare a virtual machine (VMware) or a docker container with Ubuntu 18, and transfer the file you downloaded there (or directly download them from the vm/docker itself).
5. Unpack the driver package's tar.
6. Unpack the sample root filesystem's tar and copy its content over to the "rootfs" folder in `Linux_for_Tegra/rootfs`
7. Go in `Linux_for_Tegra` and execute script `apply_binaries.sh`. It is <b>extremely</b> important to do this <b>only once</b>! Doing it more than once will corrupt the image. This script will configure the rootfs with the L4T kernel and nvidia drivers.
8. Go in `Linux_for_Tegra/tools` directory and run `l4t_create_default_user.sh` with the following arguments:
   * --username : the username (e.g. jetson)
   * --password : the password (e.g. jetson)
   * --autologin : to enable autologin without waiting for user input at boot time
   * --hostname : the name of the device (e.g. jetson)
   * --accept-license : to pre-accept the EULA license (extremely useful since it will make the system to boot immediately).
   so for instance:
  ```./l4t_create_default_user.sh --username jetson --password jetson --hostname jetson --autologin --accept-license```
9. Run `./jetson-disk-image-creator.sh` with the following arguments:
   * -o : the output's sd card image filename (must end with '.img')
   * -b : the board name (must be exactly `jetson-nano-2gb-devkit`)
   * do not use the "-r" option for the revision since it is automatically determined in the case of the nano-2gb-devkit.
10. The image is now ready. Insert the sd card in a card reader and flash the image on the sd card that was prepared before using `balena etcher` or a similar program.
11. Open a program like gparted: you'll see that the sd card will have a lot of partitions. Go and look for the one named "APP" and resize it, enlarging it to occupy all the remaining available space.
12. insert the sd card in the jetson's slot and power it on, it will boot.
13. The system will be accessible by ssh directly using as `hostname` the one that was set before during the execution of the `l4t_create_default_user.sh` script. Otherwise, one should just connect an hdmi monitor and can use the graphical interface.

#### 2.1) Alternative way

If you prefer, you can download nvidia's sdkmanager and use that to download L4T and the jetpack and build the sd card image. Just don't use that tool to flash the board directly since the Jetson's nano 2gb devkit is known to have issues with this direct procedure. Use again a tool like balena etcher to flash the image on the card.

### 3) Preparing Ubuntu 18 to Ubuntu 20.04 update

#### 3.1) Initial steps
The system you have now is very basic and it still needs some packages. First thing to do is of course to open a terminal and do: `sudo apt update` and `sudo apt upgrade`. After that, it is necessary to install the following:
1. Install all of the L4T packages: `sudo apt install nvidia-l4t-*` this will also install CUDA (it is the jetpack)

2. Edit the `.bashrc` file so as to include the path and library path to CUDA, and also the `$CUDA_HOME` variable so:
   ```
   export PATH=/usr/local/cuda/bin:$PATH
   export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
   export CUDA_HOME=/usr/local/cuda
   ```

3. Install the `miniforge` package manager. It is a very lightweight alternative to anaconda and miniconda. Besides, anaconda and miniconda don't work on the Jetson because the ARM v8 processor lacks some instructions that are needed by them. Conversely, miniforge works like a charm. Miniforge can be git-pulled from https://github.com/conda-forge/miniforge .

4. Once miniforge is up and running, install the `jtop` utility (like htop but it also shows gpu utilization. it is the nvidia-smi version for Tegra SoCs). It is installed via pip. So:
   ```
   sudo pip install -U jetson-stats
   ```

6. Install the `numba` package with gpu support. The last version to support CUDA 10.2 is the 0.56.4, so: `conda install numba=0.56.4`. It will work out of the box. To test it just open python and run the following:
   ```python
   import numba
   # this should display "True"
   numba.cuda.is_available()
   # this will show the details of the jetson's gpu
   numba.cuda.detect()
   ```

7. Install the `cupy` package with gpu support. This is done via pip and the specific version that supports CUDA 10.2 is obtained by launching:
   ```
   pip install cupy-cuda102
   ```

#### 3.2) Disabling graphical interface and update

This step is necessary during the 18 to 20.04 update, otherwise the process could break the update and the sd card would have to be flashed again.
```
sudo systemctl set default multi-user.target
```
Now, via ssh, edit the file at `/etc/update-manager/release-upgrades` with sudo and change the last line from `Prompt=never` to `Prompt=lts`. At this point all is ready for the release upgrade, so:
```
sudo do-release-upgrade
```
It will take time. After the procedure completes, reboot the board. It is possible that some errors will be shown during the boot procedure. If everything went well you should be able to login again via ssh or open up a terminal with `CTRL+ALT+F1` from a jetson-attached usb keyboard.

#### 3.3) Reparing broken packages

Some packages could have been broken during the update, so: `sudo dpkg --configure -a` will do the trick. After that, run:
```
sudo apt update
sudo apt upgrade
```
If everything went well the system is now Ubuntu 20.04. 




