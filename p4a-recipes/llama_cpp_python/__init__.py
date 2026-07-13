"""
python-for-android recipe — llama-cpp-python (İLERİ SEVİYE / DENEYSEL)

⚠️ ÖNEMLİ — LÜTFEN OKUYUN:
Bu recipe VARSAYILAN buildozer.spec `requirements` listesinde DEĞİLDİR ve
uygulama bu recipe olmadan da tamamen çalışır (core/nlp_engine.py, model
yoksa otomatik olarak kural-tabanlı STUB motoruna düşer — bkz.
p4a-recipes/README.md).

llama-cpp-python; CMake + bir C/C++ derleyicisiyle llama.cpp'yi kaynaktan
derleyen, resmi python-for-android recipe deposunda YER ALMAYAN bir
pakettir. Android NDK toolchain'ine cross-compile etmek İnce ayar
gerektirir (doğru CMAKE_TOOLCHAIN_FILE, ANDROID_ABI, ANDROID_PLATFORM,
doğru sysroot, NEON/ARM bayrakları vb.) ve resmi destek olmadığından
p4a/NDK sürüm güncellemeleriyle sık sık bozulabilir.

Bu recipe, eski sürümüne göre gerçek bir NDK CMake toolchain dosyası
kullanacak şekilde düzeltilmiştir (önceki sürüm yalnızca `setup.py
install --user` çağırıyordu ve bir cross-compile toolchain'i hiç
belirtmiyordu — bu, ya derleme hatasına ya da HOST mimarisi için
derlenmiş/çalışmayan bir ikiliğe yol açardı). Yine de bu paket
resmi/stabil kabul EDİLMEMELİDİR.

Denemek isteyen kullanıcılar için:
    1. buildozer.spec içindeki `requirements =` satırına
       `,llama-cpp-python` ekleyin.
    2. `buildozer android clean` çalıştırıp yeniden derleyin.
    3. Derleme süresi önemli ölçüde uzar (llama.cpp'nin C++ kaynaklarının
       tamamı ARM64 için derlenir) ve büyük ihtimalle NDK/CMake sürüm
       uyumsuzluklarıyla ek hata ayıklama gerekebilir.
"""

import os
from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import current_directory


class LlamaCppPythonRecipe(Recipe):
    version = "0.2.90"
    url = "https://github.com/abetlen/llama-cpp-python/archive/refs/tags/v{version}.tar.gz"
    name = "llama_cpp_python"
    depends = ["python3", "setuptools", "numpy"]
    call_hostpython_via_targetpython = False

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super().get_recipe_env(arch, with_flags_in_cc)

        ndk_dir = self.ctx.ndk_dir
        toolchain_file = os.path.join(
            ndk_dir, "build", "cmake", "android.toolchain.cmake"
        )
        api = self.ctx.ndk_api

        # CPU-only derleme; Metal/CUDA/CLBlast yok (Android'de anlamsız).
        # CMAKE_TOOLCHAIN_FILE olmadan cmake, hedef ARM64 yerine HOST
        # (x86_64 Linux) için derler ve üretilen .so cihazda yüklenemez —
        # bu satırlar bu sınıfın en kritik düzeltmesidir.
        env["CMAKE_ARGS"] = (
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file} "
            f"-DANDROID_ABI={arch.arch} "
            f"-DANDROID_PLATFORM=android-{api} "
            "-DCMAKE_BUILD_TYPE=Release "
            "-DLLAMA_METAL=OFF "
            "-DLLAMA_CUBLAS=OFF "
            "-DLLAMA_CLBLAST=OFF "
            "-DLLAMA_NATIVE=OFF "
            "-DLLAMA_BUILD_TESTS=OFF "
            "-DLLAMA_BUILD_EXAMPLES=OFF"
        )
        env["FORCE_CMAKE"] = "1"
        env["CMAKE_TOOLCHAIN_FILE"] = toolchain_file
        env["ANDROID_ABI"] = arch.arch
        env["ANDROID_PLATFORM"] = f"android-{api}"
        return env

    def build_arch(self, arch):
        with current_directory(self.get_build_dir(arch.arch)):
            hostpython = self.get_hostpython_path(arch)
            env = self.get_recipe_env(arch)
            # pip'in kendi izole build ortamını kurmasını engelle (--no-build-isolation)
            # ki CMAKE_ARGS/env değişkenleri build alt sürecine gerçekten ulaşsın.
            self.run_hostpython(
                f"-m pip install . --target={self.ctx.get_python_install_dir(arch.arch)} "
                f"--no-build-isolation --no-deps",
                env=env,
            )


recipe = LlamaCppPythonRecipe()
