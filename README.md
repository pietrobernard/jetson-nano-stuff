# Jetson Nano 2GB devkit - Ubuntu 20.04 + GPGPU packages
Everything to get the old Jetson Nano Developer Kit 2GB up and running with Ubuntu 20.04 and GPGPUs packages.

Here are the details of the board.
<table>
	<tr>
		<td>
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
					<td><b>CPU</b></td>
					<td>ARMv8 Processor rev 1</td>
				</tr>
      				<tr>
					<td><b>RAM</b></td>
					<td>2 GB LPDDR4</td>
				</tr>
				<tr>
			      		<td><b>Compute Cap.</b></td>
			      		<td>5.3 (architecture: Maxwell)</td>
			   	</tr>
			</table>
		</td>
		<td>
			<img src="img/jetson_nano.png">
		</td>
	</tr>
</table>

Official docs are available [here](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-2gb-devkit).

This document describes how to create a bootable SD card image, update to Ubuntu 20.04 and install some libraries to exploit gpgpu computing both in python (e.g. numba, cupy, cudf), c++ (nvcc, ecc) and distributed computing tools (dask). Specifically:
+ numba 0.56.4
+ cupy 12.3.0
+ pyarrow 1.0.1
+ cudf 0.19.0
+ dask 2021.04.0

<b>📝Notice📝</b>

I suggest to use a 64 GB card since it will give you plenty of space to allocate a swap partition/swap file. During the compilation of some libraries, you're going to need at least 8 GB of swap in addition to the 1 GB that is already present by default. So, if you start with a 32 GB card, you will have to clone it to a 64 GB to do that compilation and then you can clone the 32 GB partition back again on the 32 GB card when the compilation finishes. The final system with all the packages installed will leave 4.8 GB free on a 32 GB card. If you're OK with that and you don't mind cloning back and forth during the procedure, go ahead with the 32 GB card, otherwise the 64 GB one is the better choice.

### 1) Intro - The board, drivers, CUDA and Ubuntu

1. This board is centered around the Tegra X1 SoC that includes the processor (an early ARM v8 so unfortunately no SVE instructions, etc) and the GPU which is a nice 128 cores Maxwell device with compute capability 5.3. The GPU is technically an iGPU (integrated) and as such it is not a discrete device attached to the pci-e bus. This is a crucial point since the "discrete" nvidia drivers <b>won't work</b> with this gpu, even if the architecture is exactly the same to that of a discrete Maxwell gpu.
The only drivers that will work are those provided by nVidia in their "Linux 4 Tegra" (<b>L4T</b>) flavour of the Linux kernel. Since the driver version and the CUDA version must exactly match, no CUDA greater than 10.2 is supported on these devices. While the Maxwell architecture can run much higher CUDA versions, because of the gpu being integrated and the drivers being built-in in the L4T kernel, unless nvidia releases a new kernel with updated drivers, it is not possible to run CUDA beyond 10.2 (if one attempts to use a version > 10.2, the iGPU will fail to initialize and will result in random crashes, effectively breaking the system).

2. The board also does not have a BIOS/EFI chip, but it uses a special partition on the SD card (more on this later on) in order to boot the device (other jetson nano's with different SoC have instead a flash chip where the bios/efi subsystem resides, this is not the case with the 2GB developer's version). The board does however have a tiny EEPROM memory, attached to the internal i2c bus. This EEPROM is not usable by the user, but it is written by the flashing utility with initial configuration values that the SoC uses in order to setup itself and start the boot. <i>Sometimes this EEPROM is bad and needs to be re-flashed, more on this later</i>.

3. With respect to the OS, nvidia officially supports only Ubuntu 18. While it is not strictly necessary, some libraries are not supported on 18. It can be updated to Ubuntu 20.04 so as to obtain updated versions of some system libraries that are quite useful for a variety of tasks. The procedure to update the os is described later.

### 2) Creating a bootable SD card and first boot
#### 2.1) Using Nvidia's sdkmanager (requires user registration)

The easiest way to do this is to set up a virtual machine (e.g. VMware) with Ubuntu 18. Once you have it up and running, install the `sdkmanager` by Nvidia. After you've installed sdkmanager, run it choosing the correct board and JetPack version (`4.6.4`). You can check only the `Jetson OS` options and uncheck the others. This will build the image, but we'll need to modify some things about it manually. When prompted to flash the device, hit `Skip`.

Open a terminal inside Nvidia's sdk folder and look for the `Linux_for_Tegra` folder. Once there, go inside `tools` and run these scripts:
1. Create a user:
   ```bash
   sudo ./l4t_create_default_user.sh -u jetson -p jetson -n jetson --accept-license --autologin
   ```
2. Create the bootable image:
   ```bash
   sudo ./jetson-image-disk-creator.sh -o sd-blob.img -b jetson-nano-2gb-devkit
   ```
Once you've done this, you can use a tool like `balena etcher` to write `sd-blob.img` to SD card:
1. <b>Before you flash the card</b>: do a low level format, without partitioning (easy via tools like `Disks` on Ubuntu). This is absolutely mandatory otherwise the system won't boot correctly.
2. Flash the image on the card.
3. Place the card in the Jetson and power it up.

<hr>

<b>Note</b>: if you see that the board does not boot, i.e. it stays locked up displaying only the splash screen with the Nvidia logo, the onboard EEPROM might be corrupted or incorrectly configured. To resolve this issue, you'll need to place the board in recovery mode and proceed as follows:

1. Completely power off the board and with a jumper cable short the "forced recovery" pin to ground.
2. Connect the micro-usb port of the board to your pc.
3. On your pc, start the virtual machine you configured above and start the sdkmanager.
4. Connect the power supply to the board and when the board is detected, attach it to your virtual machine.
5. Open a terminal and navigate inside the "Linux_for_Tegra" folder and run, as sudo, the script "nvsdkmanager_flash.sh" without arguments. The script will attempt to connect to the board and flash it. If the script hangs at the beginning, power down the board and then power it up again. Reattach it to the VM and re-launch the script, it will work.
6. Wait for the script to finish. Once it does, the script will also write the system partitions on the SD card. At this point you'll be free to re-flash the SD card as outline above since the EEPROM configuration is independent of the SD card's contents.

<hr>

#### 2.2) Manual download of components (no user registration required)

1. Go [here](https://developer.nvidia.com/embedded/linux-tegra-r3274) and download the [Driver Package (BSP)](https://developer.nvidia.com/downloads/embedded/l4t/r32_release_v7.4/t210/jetson-210_linux_r32.7.4_aarch64.tbz2) and the [Sample Root Filesystem](https://developer.nvidia.com/downloads/embedded/l4t/r32_release_v7.4/t210/tegra_linux_sample-root-filesystem_r32.7.4_aarch64.tbz2).

2. Untar the `Driver Package` with the following:
   ```bash
   sudo tar -xpf <filename>.tbz2
   ```
   it is <b>extremely</b> important to untar as sudo and to use the `-xpf` flags. Otherwise, permissions will be screwed up and the subsequent actions won't work. This will create a folder named `Linux_for_Tegra`.

3. Move the `Sample Root Filesystem`'s tar inside `Linux_for_Tegra/rootfs` and untar it there:
   ```bash
   sudo tar -xpf <filename>.tbz2
   ```

4. Go inside the `Linux_for_Tegra` directory and launch, as sudo, the `apply_binaries.sh` script. <b>Do it ONLY ONCE</b> otherwise the image will be corrupted!

5. Go inside the `Linux_for_Tegra/tools` directory and run, as sudo, the `l4t_create_default_user.sh` script with the followings args:
   ```bash
   -u : specifies the user name (e.g. jetson)
   -p : specifies the password (e.g. jetson)
   -n : specifies the host name (e.g. jetson)
   --accept-license : already accepts the license so that the system is ready to go
   --autologin : if you want the system to autologin
   ```

6. Build the image by running, as sudo, script `jetson-disk-image-creator.sh` with the options:
   ```bash
   -o : output file (must end with .img extension)
   -b : must be exactly jetson-nano-2gb-devkit
   ```
After this, you can flash the image on the card, place it in the jetson and boot.

### 3) Prepare system for update

The first boot will show some errors, ignore them. The board will reboot automatically.

First thing to do, as usual:
```bash
sudo apt update
sudo apt upgrade
```
Remove chromium browser since otherwise it will cause problems during the update:
```bash
sudo apt --purge remove chromium-browser
```

#### 3.1) Install JetPack 4.6.4
```bash
sudo apt install nvidia-jetpack
```
The jetpack also installs all of the remaining `nvidia-l4t` packages that are needed. Edit the `.bashrc` file and add these lines at the end:
```bash
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

#### 3.2) Disable the graphical user interface
```bash
sudo systemctl set-default multi-user.target
```
and reboot the board.

#### 3.3) Unlock the release advancement option

Edit the file at `/etc/update-manager/release-upgrades`, changing the last line to `Prompt=lts`.

### 4) Upgrade

<hr>
<b>⚠️Warning⚠️</b>

If you used the second method to build the sd-card image, before you proceed you must edit the `/etc/apt/apt.conf.d/01autoremove` file adding these lines:

```bash
	"libnvidia-container-tools";
	"libnvidia-container0";
	"libnvidia-container1";
	"nvidia-container";
	"nvidia-container-csv-cuda";
	"nvidia-container-csv-cudnn";
	"nvidia-container-csv-tensorrt";
	"nvidia-container-csv-visionworks";
	"nvidia-container-runtime";
	"nvidia-container-toolkit";
	"nvidia-cuda";
	"nvidia-cudnn8";
	"nvidia-docker2";
	"nvidia-jetpack";
	"nvidia-l4t-3d-core";
	"nvidia-l4t-apt-source";
	"nvidia-l4t-bootloader";
	"nvidia-l4t-camera";
	"nvidia-l4t-configs";
	"nvidia-l4t-core";
	"nvidia-l4t-cuda";
	"nvidia-l4t-firmware";
	"nvidia-l4t-gputools";
	"nvidia-l4t-graphics-demos";
	"nvidia-l4t-gstreamer";
	"nvidia-l4t-init";
	"nvidia-l4t-initrd";
	"nvidia-l4t-jetson-io";
	"nvidia-l4t-jetson-multimedia-api";
	"nvidia-l4t-kernel";
	"nvidia-l4t-kernel-dtbs";
	"nvidia-l4t-kernel-headers";
	"nvidia-l4t-libvulkan";
	"nvidia-l4t-multimedia";
	"nvidia-l4t-multimedia-utils";
	"nvidia-l4t-oem-config";
	"nvidia-l4t-tools";
	"nvidia-l4t-wayland";
	"nvidia-l4t-weston";
	"nvidia-l4t-x11";
	"nvidia-l4t-xusb-firmware";
	"nvidia-nsight-sys";
	"nvidia-opencv";
	"nvidia-tensorrt";
	"nvidia-visionworks";
	"nvidia-vpi";
	"libdrm-tegra0";
	"nsight-systems-linux-tegra-public-2021.5.4.19-e642d4b";
```
to both the `NeverAutoRemove` and `Never-MarkAuto-Sections`. This will prevent the updater from removing these packages (it will otherwise cause a kernel panic and break the system on reboot).

<hr>

To launch the upgrade, it is best to connect a keyboard to the Jetson and an HDMI monitor. Then launch the hideous command:
```bash
sudo do-release-upgrade
```

During the procedure you might be prompted about what to do with several configuration files. Just go for the default option.

<b>⚠️ At the end, it should ask you whether you want to remove obsolete software. Do not remove it (just type enter) otherwise some of Nvidia's proprietary stuff will get deleted and the system will break.⚠️</b>

Once the system reboots (hopefully), try:
```bash
sudo apt update
```
If the command fails due to broken packages, then repair them:
```bash
sudo dpkg --configure -a
```
should do the trick.

### 5) Installing software
#### 5.1) Install htop and pip
```bash
sudo apt install htop
sudo apt install python3-pip
```

#### 5.2) Installing Miniforge package manager

Since the CPU's architecture is too old to run Anaconda or Miniconda, the other option is miniforge3. You can get it from here and install it via the script:
```bash
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
```
Then, create a new environment, I called it `gpudist`, with `python3.9`:
```bash
conda create --name=gpudist python=3.9
```

#### 5.3) Install `jetson-stats` and `jtop`
Install now the `jetson-stats` pip package from the `base` environment:
```
sudo pip3 install -U jetson-stats
```
and reboot the board. Then activate the `gpudist` env and run:
```
pip3 install jetson-stats
```
this will install the `jtop` python's module that will be useful later.

#### 5.4) Install `numba` and `cupy` with GPU support

To install numba, we'll have to get the highest version that supports CUDA 10.2 that is the 0.56.4. So:
```bash
conda install numba=0.56.4
```
and then test it opening a python session:
```bash
from numba import cuda
cuda.is_available()
cuda.detect()
```
this should look like:
```bash
Python 3.9.19 | packaged by conda-forge | (main, Mar 20 2024, 13:51:08) 
[GCC 12.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from numba import cuda
>>> cuda.is_available()
True
>>> cuda.detect()
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
True
>>> 
```
Now it's time for `cupy` with GPU support. It is quite easy:
```bash
pip install cupy-cuda102
```
To test it open a python session and:
```bash
from cupy import cuda
```
if it doesn't show errors, then it works.

### 6) Building Arrow

Before doing anything, we have to use a version of gcc/g++ that is `≤ 8`. Install `g++-8` via apt and then, after having removed `/usr/bin/gcc` and `/usr/bin/g++` do:
```bash
sudo ln -s gcc-8 /usr/bin/gcc
sudo ln -s g++-8 /usr/bin/g++
```

#### 6.1) Prerequisites

Install `CMake` version `3.18` via conda:
```bash
conda install cmake=3.18
```

Then, clone `Arrow` repo via git and checkout version `1.0.1`:
```bash
git clone https://github.com/apache/arrow.git
cd arrow
git checkout apache-arrow-1.0.1
```
Edit the `.bashrc` file and add, assuming arrow is in $HOME:
```bash
export ARROW_HOME=${HOME}/arrow/cpp
export LD_LIBRARY_PATH=${HOME}/arrow/cpp/lib:$LD_LIBRARY_PATH
```
reload the `.bashrc` so that these vars will be exported.

#### 6.2) Download and build Boost libraries

We need boost version 1.71.0 which can be downloaded directly:
```bash
wget https://archives.boost.io/release/1.71.0/source/boost_1_71_0.tar.gz
```
go inside `boost_1_71_0` folder and run the following:
```bash
mkdir install
./bootstrap.sh --prefix=${PWD}/install --exec-prefix=${PWD}/install
```
this will build the `b2` program. Start the build via:
```bash
./b2 -j4
```
at this point, assuming you've got the boost libs in `$HOME/boost_1_71_0`, you'll have the include path in `$HOME/boost_1_71_0` (folder `boost`) and the lib path in `$HOME/boost_1_71_0/stage/lib`. We can thus add to the .bashrc the following lines:
```bash
export LD_LIBRARY_PATH=/path/to/boost/boost_1_71_0/stage/lib:$LD_LIBRARY_PATH
export BOOST_ROOT=/path/to/boost/boost_1_71_0
export BOOST_INCLUDEDIR=/home/jetson/boost_1_71_0/boost
export BOOST_LIBRARYDIR=/home/jetson/boost_1_71_0/stage/lib
```
these vars will be used in the following to build Arrow. Also, create two links:
```
ln -s ${BOOST_ROOT}/boost ${BOOST_ROOT}/include
ln -s ${BOOST_ROOT}/stage/lib ${BOOST_ROOT}/lib
```
these will be useful since some packages like to find boost libs at those locations.

#### 6.3) Configure cmake for Arrow
Now go to `${ARROW_HOME}/cpp/thirdparty`. You'll see a file named `versions.txt`. Open it and in the `DEPENDENCIES` section below, delete the entry corresponding to `boost`, since we've already installed it. Also, in the line corresponding to `c-ares`, substitute the link with this static one: `https://github.com/c-ares/c-ares/releases/download/cares-1_16_1/c-ares-1.16.1.tar.gz`. Save the file and run the `donwload_dependencies.sh` script.

Proceed to build and install `thrift` manually, since it fails in the automated procedure. Go in `${ARROW_HOME}/cpp/thirdparty` and untar the `thrift` tarball. Then go inside its folder and:

After that, configure with:
```bash
mkdir install
./bootstrap.sh
./configure CPPFLAGS="-I${BOOST_ROOT}" CXXFLAGS="-fPIC" --with-boost=${BOOST_ROOT} --prefix=${PWD}/install
make -j4
sudo make install
export THRIFT_ROOT=${PWD}/install
```
Add a `.conf` file for Thrift in `/etc/ld.so.conf.d`. The file should be called `thrift.conf` and should contain the line given by the command:
```bash
echo ${THRIFT_ROOT}/lib
```
which in my case is: `/home/jetson/arrow/cpp/thirdparty/thrift-0.12.0/install/lib`. Save the file as sudo and then:
```bash
sudo ldconfig
```
Now, edit the `versions.txt` file again and remove the line corresponding to `thrift` in the `DEPENDENCIES` section.

Now, go back in the `cpp` folder and create a `build` dir, go inside that and type:
```bash
cmake   -DCMAKE_INSTALL_PREFIX=${ARROW_HOME} \
        -DCMAKE_CXX_FLAGS="-I${CONDA_PREFIX}/include -fPIC" \
        -DARROW_COMPUTE=ON \
        -DARROW_CSV=ON \
        -DARROW_CUDA=ON \
        -DARROW_FILESYSTEM=ON \
        -DARROW_ORC=ON \
        -DARROW_PARQUET=ON \
        -DARROW_PYTHON=ON \
        -DARROW_DATASET=ON \
        -DARROW_HDFS=ON \
        -DARROW_JSON=ON \
        -DARROW_BUILD_BENCHMARKS=OFF \
        -DARROW_BUILD_EXAMPLES=OFF \
        -DARROW_BUILD_TESTS=OFF \
        -Dabsl_SOURCE=BUNDLED \
        -DAWSSDK_SOURCE=BUNDLED \
        -Dbenchmark_SOURCE=BUNDLED \
        -DBoost_SOURCE=SYSTEM \
        -DBrotli_SOURCE=BUNDLED \
        -DBZip2_SOURCE=BUNDLED \
        -Dc-ares_SOURCE=BUNDLED \
        -Dgflags_SOURCE=BUNDLED \
        -Dglog_SOURCE=BUNDLED \
        -Dgoogle_cloud_cpp_storage_SOURCE=BUNDLED \
        -DgRPC_SOURCE=BUNDLED \
        -DGTest_SOURCE=BUNDLED \
        -Djemalloc_SOURCE=BUNDLED \
        -DLLVM_SOURCE=BUNDLED \
        -DLz4_SOURCE=BUNDLED \
        -Dnlohmann_json_SOURCE=BUNDLED \
        -Dopentelemetry-cpp_SOURCE=BUNDLED \
        -DORC_SOURCE=BUNDLED \
        -Dre2_SOURCE=BUNDLED \
        -DProtobuf_SOURCE=BUNDLED \
        -DRapidJSON_SOURCE=BUNDLED \
        -DSnappy_SOURCE=BUNDLED \
        -DSubstrait_SOURCE=BUNDLED \
        -DThrift_SOURCE=SYSTEM \
        -Ducx_SOURCE=BUNDLED \
        -Dutf8proc_SOURCE=BUNDLED \
        -Dxsimd_SOURCE=BUNDLED \
        -DZLIB_SOURCE=BUNDLED \
        -DZSTD_SOURCE=BUNDLED \
        -DBoost_ROOT=${BOOST_ROOT} \
        -DThrift_ROOT=${THRIFT_ROOT} \
        -DTHRIFT_STATIC_LIB=${THRIFT_ROOT}/lib/libthrift.a \
	..
```
cmake could produce some warning due to some variables not being used. Don't worry about them.

Before you go ahead with the building, go inside the `cpp/thirdparty/` and untar the `protobuf` tarball. Enter the folder and install the python module:
```bash
python setup.py build_ext --inplace
python setup.py install
```
This will be useful for later.

After that, proceed with the build:
```bash
make -j4
make install
```
Create a static link to `protoc`:
```bash
sudo ln -s ${ARROW_HOME}/build/protobuf_ep-install/bin/protoc-3.12.1.0 /usr/bin/protoc
```
After that, go in the `arrow/python` folder. Set this env vars:
```bash
export PYARROW_WITH_CUDA=1
export PYARROW_WITH_PARQUET=1
export PYARROW_WITH_ORC=1
export PYARROW_WITH_DATASET=1
```
Install `cython` version `0.29`. This is very important since newer versions won't work.
```
conda install cython=0.29
```
Now, edit the `SetupCxxFlags.cmake` script inside `python/cmake_modules`. The Jetson's a little picky with processor architecture. Go at line 76 and comment the two lines that are there and write this instead:
```cmake
set(CXX_SUPPORTS_ARMV8_ARCH 1)
```
Now you can run the setup with the following (it will build with only one core which is good since it requires a lot of memory and the Jetson doesn't have nearly as much to do it with more than one):
```bash
python setup.py build_ext --build-type=release --bundle-arrow-cpp bdist_wheel
```
After this completes, you'll find the wheel inside the `dist` folder. Go in that folder and (in my case):
```bash
pip install pyarrow-1.0.1.dev0+g886d87bde.d20240614-cp39-cp39-linux_aarch64.whl
```
Open a python session and try the following:
```bash
import pyarrow
from pyarrow import cuda
```
If it doesn't give any errors, then you're good and pyarrow is installed correctly in the system.

### 7) Building cuDF
Start by cloning cuDF's repo:
```bash
git clone https://github.com/rapidsai/cudf.git
cd cudf
git checkout v0.19.0
```
Now we have to install some packages.

#### 7.1) Build Pandas

We'll need version `1.2.4` exactly.
```bash
cd $HOME
mkdir pandas_src && cd pandas_src
git clone https://github.com/pandas-dev/pandas.git
cd pandas
git checkout v1.2.4
python setup.py install
```

#### 7.2) Build DLpack

We will need version `0.3`.
```bash
git clone https://github.com/dmlc/dlpack.git
cd dlpack
git checkout v0.3
mkdir install
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=${PWD}/../install ..
make -j4
make install
```
Then, export this var and also write this inside the `.bashrc` file:
```bash
export DLPACK_ROOT=/your/path/to/dlpack
```

#### 7.3) Build RMM

RMM needs to be of the same version of `cuDF` (0.19.0).
```bash
git clone --recurse-submodules https://github.com/rapidsai/rmm.git
cd rmm
git checkout v0.19.0
mkdir install
mkdir build && cd build
```
Now, even if `rmm/cmake/Modules/SetGPUArchs.cmake` file, at line 17, does not contain "53" in the list of supported architectures, it doesn't matter because we're going to force it:
```bash
# now force the compilation for the current arch only (53)
cmake -DCMAKE_INSTALL_PREFIX=${PWD}/../install -DCMAKE_CUDA_ARCHITECTURES="" ..
make -j4
make install
cd ..
```
Then export and write this in the `.bashrc` file:
```bash
export RMM_ROOT=${PWD}
export LD_LIBRARY_PATH=${PWD}/install/lib:$LD_LIBRARY_PATH
```
Install also the python module. Go in the `rmm/python` folder. The `setup.py` file needs a little editing since, as you may expect, CUDA for the Tegra SoC is a little different.

+ go at line 56 and add below the following:
  ```python
  cuda_stubs_dir = os.path.join(CUDA_HOME, "lib64/stubs")
  ```
+ go at line 60 and edit the line so that it will look like this:
  ```python
  INSTALL_PREFIX = os.environ.get("RMM_ROOT", False)
  ```
+ go now at line 116 and add to the `library_dirs` list the `cuda_stubs_dir` so that it will look like this:
  ```python
  library_dirs = [
    	get_python_lib(),
    	os.path.join(os.sys.prefix, "lib"),
    	cuda_lib_dir,
    	cuda_stubs_dir,
  ]
  ```

Now you're ready to do the following:
```bash
python setup.py build_ext --inplace
python setup.py install
```

#### 7.4) Build cuDF

<b>⚠️Warning⚠️</b>

In order to build cuDF you're going to need a 8 GB swap file/partition. If you are using a 32 GB card, there won't be enough space at this point. So, clone the card onto a 64 GB one and create a swap partition in the 32 GB unallocated space and then put the 64 GB card in the board. At this point you can build cuDF. When you're done building cuDF, clone the 32 GB partition back on the old 32 GB card.

Export this variable and also write it to the `.bashrc` file:
```bash
export CUDF_HOME=/your/path/to/cudf/download
```
Then proceed:
```bash
cd $CUDF_HOME/cpp
mkdir install
mkdir build && cd build
```
And build `cuDF`:
```bash
cmake	-DMAKE_INSTALL_PREFIX=${PWD}/../install \
	-DCMAKE_CXX11_ABI=ON \
	-DRMM_INCLUDE=${RMM_ROOT}/include \
	-DDLPACK_INCLUDE=${DLPACK_ROOT}/include \
	-DGPU_ARCHS="" \
	-DCMAKE_CUDA_ARCHITECTURES="" \
	..
make -j1
sudo make install
```
The build will take approximately 18 hours on a class 10, A1, microSDXC UHS-I card (rated at a nominal speed of 140 MB/s).

When the build completes, export the following variable and edit again the `.bashrc` file and write these lines:
```bash
export CUDF_ROOT=${CUDF_HOME}/cpp/build
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH/usr/local/lib:
```
Finally, as sudo:
```bash
sudo ldconfig
```

Go inside `${CUDF_HOME}/python/cudf` and edit the `setup.py` file in the following manner. Consider the code block from line 165 (it starts with `extensions = [`) up to line 199 (it ends with `]`). Add the lines that are marked below between the comments. Of course you should input the path that corresponds to your installation. If you've followed exactly what I've done before, then you can copy and paste the code below:
```python
extensions = [
    Extension(
        "*",
        sources=cython_files,
        include_dirs=[
            os.path.abspath(os.path.join(CUDF_HOME, "cpp/include/cudf")),
            os.path.abspath(os.path.join(CUDF_HOME, "cpp/include")),
            os.path.abspath(os.path.join(CUDF_ROOT, "include")),
            os.path.join(CUDF_ROOT, "_deps/libcudacxx-src/include"),
            os.path.join(CUDF_ROOT, "_deps/dlpack-src/include"),
            os.path.join(
                os.path.dirname(sysconfig.get_path("include")),
                "libcudf/libcudacxx",
            ),
            os.path.dirname(sysconfig.get_path("include")),
            # THE FOLLOWING TWO LINES HAVE BEEN ADDED
            os.path.join("/usr/local/include/libcudf/libcudacxx"),
            os.path.join("/usr/local/include"),
            os.path.join("/home/jetson/dlpack/install/include"),
            # END OF EDIT
            np.get_include(),
            pa.get_include(),
            cuda_include_dir,
        ],
        library_dirs=(
            pa.get_library_dirs()
            + [
                get_python_lib(),
                os.path.join(os.sys.prefix, "lib"),
                # THE FOLLOWING LINE HAS BEEN ADDED
                os.path.join("/usr/local/lib"),
                os.path.join("/home/jetson/dlpack/install/lib"),
                # END OF EDIT
                cuda_lib_dir,
            ]
        ),
        libraries=["cudart", "cudf"] + pa.get_libraries() + ["arrow_cuda"],
        language="c++",
        extra_compile_args=["-std=c++14"],
    )
]
```
Then go on with the build:
```bash
python setup.py build_ext --inplace
python setup.py install
```
Then go in the home directory and open a python session and try importing cudf. You should see the following message:
```bash
>>> import cudf
/home/jetson/miniforge3/envs/gpudist/lib/python3.9/site-packages/cudf-0.19.0+0.gf07b25103e.dirty-py3.9-linux-aarch64.egg/cudf/utils/gpu_utils.py:92: UserWarning: You will need a GPU with NVIDIA Pascal™ or newer architecture
Detected GPU 0: NVIDIA Tegra X1 
Detected Compute Capability: 5.3
  warnings.warn(
>>> 
```
If everything went well, check that the GPU is being used in this manner: open another ssh session and run `jtop` in it. From the other session, in the python terminal run these commands:
```python
import cudf as cf
import pandas as pd
import numpy as np
df = pd.DataFrame(np.arange(10**5))
cdf = cf.from_pandas(df)
```
The very last command should trigger the GPU and you'll see on jtop the GPU utilization spiking and the shared memory rising like so:
<p align="center"><img src="img/jtop_screen.png"></p>

<b>⚠️Warning⚠️: interaction between cupy and cudf</b>

If you're using cudf and cupy at the same time, always import `cudf` as the first. If you don't do this, for instance if you import first cupy and then cudf, the import will fail due to the fact that cupy initializes certain env and iGPU device properties that will wreak havoc with cudf. On the contrary, if you always import cudf (or Dask-cudf) first, everything will work. I've only found this behaviour with this older version so maybe it's a bug that has been solved in the future releases or it might be due to the unique nature of the Jetson's hardware. Conversely, with other packages like numba, etc cudf doesn't care whether it is imported first or not.

<b>📝Notice📝</b>

Since this is hardly the most up-to-date version of `cuDF`, some features are not available (they actually throw out NotImplemented exceptions) so be careful when dealing with projects that require higher versions of this package. You can find the complete description in the [RAPIDS documentation](https://docs.rapids.ai/api/cudf/stable/user_guide/cupy-interop/).

### 8) Dask with Dask-cuDF package

As dask's [official docs](https://docs.dask.org/en/stable/gpu.html) say, GPU support is orthogonal to dask. When work is distributed across the nodes, dask calls the function/methods that have been inputted by the user. If these functions/methods are built to use GPUs, they will trigger the GPU. So, for instance, if in a computation you substitute numpy arrays with cupy ones, the GPU will be triggered. Same goes if you use cudf's DataFrames instead of pandas' ones. The `Dask-cudf` package takes it a step further and allows to 'easily' bridge between the two worlds.

#### 8.1) Building dask itself
We're going to need `dask 2021.04.0` and then we'll build the `Dask-cuDF` module. Go in the home dir and download dask:
```bash
git clone https://github.com/dask/dask.git
cd dask
git checkout 2021.04.0
```
and then proceed to build and install:
```bash
python setup.py build_ext --inplace
python setup.py install
```

#### 8.2) Building distributed

Start by cloning the github repo:
```bash
git clone https://github.com/dask/distributed.git
cd distributed
git checkout 2021.04.0
```
Before building and installing this package, we need to firstly install `click 7.1.2` (versions higher than this will cause fails) and `tornado 6.4`:
```bash
conda install click=7.1.2
conda install tornado=6.4
```
It is OK if conda installs tornado 6.4.1. Now, the system is ready to build distributed:
```bash
python setup.py build_ext --inplace
python setup.py install
```

#### 8.3) Building Dask-cuDF
Go back to `${CUDF_HOME}/python/Dask-cuDF` folder and:
```bash
python setup.py build_ext --inplace
python setup.py isntall
```
Go now in the home directory and open a python terminal. Try:
```python
import dask_cudf
```
it should display a message just like the one we had when importing `cudf`. Here you can find [RAPIDS 10 minutes guide to `cuDF` and `Dask-cuDF`](https://docs.rapids.ai/api/cudf/stable/user_guide/10min/). As it was said before, notice that some of these examples do not work because at the time these versions were released, some features were still under development and will throw `NotImplemented` errors.

#### 8.4) Installing the Dask-cuDF dashboard

We need to install two packages: `Bokeh 2.2.3` and `jinja2 3.0.0` (it must be exactly 3.0.0 otherwise it will fail) via conda:
```bash
conda install bokeh=2.2.3
conda install jinja2=3.0.0
```
After you've done this, download from this repo the `distributed.zip` and `jtop.zip` archives. Unzip these archives and copy them over the `site-packages` folder of the python interpreter that is running in your env. In my case its gpudist so I have to copy them over to:
```bash
/home/jetson/miniforge3/envs/gpudist/lib/python3.9/site-packages/distributed-2021.4.0-py3.9.egg/
/home/jetson/miniforge3/envs/gpudist/lib/python3.9/site-packages/jtop/
```
Overwrite all the files that you'll get prompted to. This will install my modifications of the dashboard so that you'll be able to check on the `GPU` (the default dashboard does not support Tegra devices...). The jtop modification simply adds a wrapper to a function in order to suppress some of its output.

After you've done this, you are ready to start a scheduler via the `dask-scheduler` command and workers via `dask-worker`. For instance in my setup I have 4 jetson nanos: one acts as the scheduler and three as workers. The scheduler is started on machine host `jetson` while the workers in `jetson-worker-1`, `jetson-worker-2` and `jetson-worker-3`. For instance in the case of the `jetson-worker-1`:
```bash
dask-worker tcp://jetson:8786 --name jetson-worker-1
```
Some test scripts are provided in the `tests` folder and [they have been written based on this article](https://www.kaggle.com/code/beniel/03-introduction-to-dask-and-dask-cudf). Below is an example of the GPU app when using an Nvidia c++ program to test the device (it involved some linear algebra calculations):
<p align="center">
	<img src="img/dashb.gif">
</p>
The app will show each the GPUs available on the cluster. The first plot shows the GPU core frequencies (absolute), the second the GPU utilization (percentage) and the third the GPU memory usage (absolute). The y-axis label is like `idx:X_worker:Y` where `idx` is the unique index of the GPU and `worker` is the unique index of the worker that GPU belongs to. In this way you always know who's doing what.

#### 8.5) Remarks on Dask-cuda

In theory, there could be more than one GPU per worker node. This is not the case of the Nano of course but in general it can be true. In order to exploit multi GPUs nodes better, dask ships the `dask-cuda` package to easily distribute work across multiple GPUs on the same node and across the other nodes. This package works also with just one GPU but <b>it doesn't work on the Jetson Nano platform</b>. This is, as it happened before, due to the unique nature of the Tegra SoC. The package is in fact built upon `libnvidia-ml` library which is <b>not</b> supported on this platform.
