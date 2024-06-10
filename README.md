# jetson-nano-stuff
Everything to get the old Jetson Nano Developer Kit 2GB up and running with Ubuntu 20.04 and a lot of other things. This board is no longer in production as of 2024 but if you still have one (or more) of these and you want to play around with it, this document will help.

Here are the details of the board.
<table>
   <tr>
      <td><b>Name</b></td>
      <td>NVIDIA Jetson Nano 2GB Developer Kit</td>
   </tr>
   <tr>
      <td><b>Part</b></td>
      <td>p3448</td>
   </tr>
   <tr>
      <td><b>SoC</b></td>
      <td>tegra210 (codename: Batuu)</td>
   </tr>
   <tr>
      <td><b>Compute Capability</b></td>
      <td>5.3 (architecture: Maxwell)</td>
   </tr>
</table>

Official docs are available [here](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-2gb-devkit).

This document describes how to create a bootable SD card image, update to Ubuntu 20.04 and install some libraries to exploit gpu computing both in python (e.g. numba, cupy, cudf) and c++ tool (nvcc, ecc). Also, directions to use distributed computing tools (dask, kafka) will be given.

### 1) Intro - The board, drivers, CUDA and Ubuntu

1. This board is centered around the Tegra SoC that includes the processor (an early ARM v8 so unfortunately no SVE instructions, etc) and the GPU which is a nice 128 cores Maxwell device with compute capability 5.3. The GPU is technically an iGPU (integrated) and as such it is not a discrete device attached to the pci-e bus. This is a crucial point since the "discrete" nvidia drivers <b>won't work</b> with this gpu, even if the architecture is exactly the same to that of a discrete Maxwell gpu.
The only drivers that will work are those provided by nVidia in their "Linux 4 Tegra" (<b>L4T</b>) flavour of the Linux kernel. Since the driver version and the CUDA version must exactly match, no CUDA greater than 10.2 is supported on these devices. While the Maxwell architecture can run much higher CUDA versions, because of the gpu being integrated and the drivers being built-in in the L4T kernel, unless nvidia releases a new kernel with updated drivers, it is not possible to run CUDA beyond 10.2 (if one attempts to use a version > 10.2, the iGPU will fail to initialize and will result in random crashes, effectively breaking the system).

2. The board also does not have a BIOS/EFI chip, but it uses a special partition on the SD card (more on this later on) in order to boot the device (other jetson nano's with different SoC have instead a flash chip where the bios/efi subsystem resides, this is not the case with the 2GB developer's version).

3. With respect to the OS, nvidia officially supports only Ubuntu 18. While it is not necessary, it can be updated to Ubuntu 20.04 so as to obtain updated versions of some system libraries that are quite useful for a variety of tasks. The procedure to update the os is described later.

### 2) Creating a bootable SD card and first boot

The ideal minimum would be a <b>64 GB</b> card, class 10, so that you can enjoy better performance from the system. A 32 GB could work too but you'd only have a little more of 1 GB of usable space and this would not allow to allocate enough space for a swap file. The 2 GB of onboard memory + the default 1 GB swap is enough for most task but the memory gets quickly eaten away if you have to compile libraries and you'll need at least another 8 GB of swap file (assuming of course you use only 1 core during the compilation).

1. Do a <b>low level format</b> of the sd card, without a filesystem. This is important, otherwise the system won't boot or, in case it does, it could be unstable.

2. Go [here](https://developer.nvidia.com/embedded/linux-tegra-r3274) and download:
   1. The [driver package (BSP)](https://developer.nvidia.com/downloads/embedded/l4t/r32_release_v7.4/t210/jetson-210_linux_r32.7.4_aarch64.tbz2) which is actually the Linux 4 Tegra.
   2. The [sample root filesystem](https://developer.nvidia.com/downloads/embedded/l4t/r32_release_v7.4/t210/tegra_linux_sample-root-filesystem_r32.7.4_aarch64.tbz2) which is Ubuntu 18.

3. Prepare a virtual machine (like VMware or Virtualbox) or a docker container with Ubuntu 18, and transfer the file you downloaded there (or directly download them from the vm/docker itself).

4. Unpack the driver package's tar.

5. Unpack the sample root filesystem's tar and copy its content over to the "rootfs" folder in `Linux_for_Tegra/rootfs`

6. Go in `Linux_for_Tegra` and execute script `apply_binaries.sh`. It is <b>extremely</b> important to do this <b>only once</b>! Doing it more than once will corrupt the image. This script will configure the rootfs with the L4T kernel and nvidia drivers.

7. Go in `Linux_for_Tegra/tools` directory and run `l4t_create_default_user.sh` with the following arguments:
   * --username : the username (e.g. jetson)
   * --password : the password (e.g. jetson)
   * --autologin : to enable autologin without waiting for user input at boot time
   * --hostname : the name of the device (e.g. jetson)
   * --accept-license : to pre-accept the EULA license (extremely useful since it will make the system to boot immediately).
   so for instance:
  ```./l4t_create_default_user.sh --username jetson --password jetson --hostname jetson --autologin --accept-license```

8. Run `./jetson-disk-image-creator.sh` with the following arguments:
   * -o : the output's sd card image filename (must end with '.img')
   * -b : the board name (must be exactly `jetson-nano-2gb-devkit`)
   * do not use the "-r" option for the revision since it is automatically determined in the case of the nano-2gb-devkit.

9. The image is now ready. Insert the sd card in a card reader and flash the image on the sd card that was prepared before using [balena etcher](https://etcher.balena.io/) or a similar program.

10. When flashing is complete, open a program like gparted. You'll see that the sd card will have a lot of partitions. Go and look for the one named "APP" and resize it, enlarging it to occupy all the remaining available space.

11. Insert the sd card in the jetson's slot and power it on, it will boot. Please notice that first boot could take a while and I'd recommend to hook up an hdmi display to catch all the output easily or, in case you have it, a serial debugger on the RX/TX ports.

12. The system will be accessible by ssh directly using as `hostname` the one that was set before during the execution of the `l4t_create_default_user.sh` script. Otherwise, you could just connect a USB keyboard and a monitor.

#### 2.1) Alternative way

If you prefer, you can download [nvidia's sdkmanager](https://developer.nvidia.com/sdk-manager) inside the virtual machine. Please notice that in this case <b>virtualbox will not work</b>. If you don't want to use docker, then you'll have to use VMware. After you install the sdk-manager, proceed as follows:

1. Format the sd card as said above and then insert it into the jetson's slot.
2. Put the jetson in forced recovery mode by shorting pin `FC REC` to ground, then connect the board to you computer via the micro USB port.
3. Power up the jetson by connecting the USB-C connector to the power supply and, if prompted by the virtual machine, connect the USB device to it.
4. Open the sdk-manager, it will detect the board. Use the menus to download the latest supported jetpack (4.6.4).
5. Choose a suitable download directory for the packages but also choose the options so as to not to flash the device.
6. After the program finishes downloading, close the sdk-manager and navigate to the download dirs. You should find a folder that is called `Linux_for_Tegra` as above. At that  point proceed as points 6 and 7 above.
7. After point 7 is completed, instead of building the image, use the script `nvsdkmanager_flash.sh` which is inside the `Linux_for_Tegra/tools` directory. Run it first with `-h` or `--help` argument so as to get a list of options that are self-explanatory.
8. The script will attempt to access the SD card inside the jetson's slot and flash it with the system image directly. Please notice that, at least on this version of the nano, this procedure could hang and fail. If you see that the prompt is not responsive for a lot of time (like an hour or so) then the script has failed. In this case, power down the board by removing the USB-C connector and power it up again. Then give it another try at point 7.
9. The script might fail several times but in the end, if it succeeds, the board will be ready to go.

### 3) Preparing Ubuntu 18 to Ubuntu 20.04 update

#### 3.1) Initial steps
The system you have now is very basic and it still needs some packages. First thing to do is of course to open a terminal and do:
```
sudo apt update
sudo apt upgrade
```
After that, it is necessary to install the following:

1. Install all of the L4T packages (the JetPack):
   ```
   sudo apt install nvidia-l4t-*
   ```
   this will also install CUDA.

2. Edit the `.bashrc` file so as to include the path and library path to CUDA, and also the `$CUDA_HOME` variable that will come in handy later. So:
   ```
   export PATH=/usr/local/cuda/bin:$PATH
   export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
   export CUDA_HOME=/usr/local/cuda
   ```

3. Install the `miniforge` package manager. It is a very lightweight alternative to anaconda and miniconda. Besides, anaconda and miniconda don't work on the Jetson because the ARM v8 processor lacks some instructions that are needed by them. Conversely, miniforge works like a charm. Miniforge can be git-pulled from https://github.com/conda-forge/miniforge .

4. Create a conda environment with ```python3.9``` since it is the most compatible version with all the libraries and packages that will be installed later. Activate the environment when done.

5. Install the `jtop` utility. It is like htop but it also shows gpu utilization and will be useful later. It is the counterpart for the Tegra SoC of the `nvidia-smi` tool that nvidia ships with discrete gpu drivers. It is installed via pip. So:
   ```
   sudo pip install -U jetson-stats
   ```

6. Install the `numba` package with gpu support. The last version to support CUDA 10.2 is the 0.56.4, so:
   ```
   conda install numba=0.56.4
   ```
   It will work out of the box. To test it just open python and run the following:
   ```python
   from numba import cuda
   # this should display "True"
   cuda.is_available()
   # this will show the details of the jetson's gpu
   cuda.detect()
   ```
   The output will be something along:
   ```
   Found 1 CUDA devices
   id 0      b'NVIDIA Tegra X1'                              [SUPPORTED]
                      Compute Capability: 5.3
                           PCI Device ID: 0
                              PCI Bus ID: 0
                                    UUID: GPU-a220528a-4ef6-34d2-ac51-72ebc267ecf9
                                Watchdog: Enabled
             FP32/FP64 Performance Ratio: 32
   Summary:
	1/1 devices are supported
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

### 4) Building and installing cuDF

Rapids is officially <b>not</b> supported on this board. Official packages only support GPUs with compute capability 6+ and architectures starting with Pascal (incidentally Pascal is the successor of Maxwell). Luckily, it is possible to run it anyway on our Maxwell 5.3 GPU but it requires a full compilation from the ground up of cuDF and most of the other libraries and packages it depends on. Be forewarned that the whole process can easily take up to 1.5-2 days to complete.

#### 4.1) Build Apache Arrow and pyarrow module

We need version `1.0.1` exactly. So:
```bash
git clone https://github.com/apache/arrow.git
cd arrow
git checkout apache-arrow-1.0.1
# these two env vars are not strictly necessary but are suggested
export PARQUET_TEST_DATA="${PWD}/cpp/submodules/parquet-testing/data"
export ARROW_TEST_DATA="${PWD}/testing/data"
```
Export then the following vars:
```bash
export ARROW_HOME=${PWD}
export LD_LIBRARY_PATH=${PWD}/lib:$LD_LIBRARY_PATH
```
Now it's time to build some dependencies that Arrow needs. 

##### 4.1.1) Build Boost libraries

##### 4.1.2) Build orc

Now we can build Arrow and pyarrow:
```bash
mkdir build && cd build

cmake	-DCMAKE_INSTALL_PREFIX=$ARROW_HOME \
	-DCMAKE_INSTALL_LIBDIR=lib \
	-DARROW_FLIGHT=ON \
	-DARROW_GANDIVA=ON \
	-DARROW_ORC=ON \
	-DARROW_PARQUET=ON \
	-DARROW_PYTHON=ON \
	-DARROW_PLASMA=ON \
	-DARROW_CUDA=ON \
	-DARROW_COMPUTE=ON \
	-DARROW_CSV=ON \
	-DARROW_FILESYSTEM=ON \
	-DARROW_WITH_BZ2=ON \
	-DARROW_WITH_ZLIB=ON \
	-DARROW_WITH_ZSTD=ON \
	-DARROW_WITH_LZ4=ON \
	-DARROW_WITH_SNAPPY=ON \
	-DARROW_WITH_BROTLI=ON \
	..

make -j1
make install
```
In this case it is mandatory to use only one core to compile, otherwise the nano will quickly run out of memory and the CPU will stall. If this process gives out any error, it is usually due to some other missing libraries. Just install them if prompted. After the building completes, the python wheel can be created. Before we do that, we have to make sure that `cython` is of the correct version (newer versions of `cython` will wreak havoc with this and further builds):
```
conda install cython=0.29.37
```
After you've done this, proceed to build the wheel:
```bash
cd $ARROW_HOME/python
export PYARROW_WITH_PARQUET=1
export PYARROW_WITH_CUDA=1
export PYARROW_WITH_ORC=1
python setup.py build_ext --build_type=release --bundle-arrow-cpp bdist_wheel
```
When the process completes, the wheel will be inside the `$ARROW_HOME/python/dist` folder. Go to that folder and install the wheel via:
```
pip install wheel_name.whl
```
Then open python and try the following:
```python
from pyarrow import cuda
```
If it doesn't show errors, it means that pyarrow has been built correctly with CUDA support enabled.

#### 4.2) Build DLPack

In the following example snippet I assume that dlpack's source folder is download in `$HOME`. Also, I'd recommend to use no more than 2 cores during compilation to avoid stalling the CPU due to low memory (even with swap active).
```
git clone https://github.com/dlmc/dlpack.git
cd dlpack
mkdir install
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/dlpack/install
make -j2
make install
```
After that, go inside the `install` dir and copy the contents of `lib` to:
```
$CONDA_PREFIX/lib
```
and the contents of `include` to:
```
$CONDA_PREFIX/include
```

#### 4.3) 


