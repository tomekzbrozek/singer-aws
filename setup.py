from setuptools import setup

setup(
    name='singer-aws',
    version='0.0.1',
    description='CLI tool for easy execution of Singer Taps, managing module dependencies and persistence of state files and config files in AWS.',
    author='tomekzbrozek',
    url='https://github.com/tomekzbrozek/singer-aws',
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    py_modules=['singer_aws'],
    install_requires=[],
    entry_points=
    '''
      [console_scripts]
      singer-aws-sync=singer_aws.main:main
      singer-aws-discover=singer_aws.discover:main
      singer-aws-install=singer_aws.install_venvs:main
    ''',
    packages=["singer_aws"],
    include_package_data=True,
)
