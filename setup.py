from setuptools import setup, find_packages
import versioneer

setup(
    name='badger-opt',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='Core of the Badger optimizer',
    url='https://github.com/SLAC-ML/Badger',
    author='Zhe Zhang',
    author_email='zhezhang@slac.stanford.edu',
    license='GPL',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'pandas',
        'pyyaml',
        'coolname',
        'pyqt5',
        'pyqtgraph',
        'qdarkstyle',
        'pillow',
        'requests',
        'tqdm',
        'xopt'
    ],
    extras_require={
        'dev': [
            'pytest',
            'pytest-qt',
            'pytest-mock'
        ]
    },
    python_requires='>=3.9',
    entry_points={
        'console_scripts': [
            'badger = badger.__main__:main'
        ]
    },
)
