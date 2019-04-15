from setuptools import setup


setup(
    name='ibtab',
    version='0.1.0',
    install_requires=[],
    packages=['ibtax'],
    entry_points={
        'console_scripts': [
            'ibtaxctl = ibtax.main:main',
        ]
    },
    include_package_data=True,
    zip_safe=False,
)
