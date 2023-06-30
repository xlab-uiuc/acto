from distutils.core import setup, Extension

setup(name='patch_mro',
      version="1.0.0",
      description="Python interface for patching mro",
      author="Kashun Cheng",
      author_email="kashun@berkeley.edu",
      ext_modules=[Extension('patch_mro', ['patch.c'])])
