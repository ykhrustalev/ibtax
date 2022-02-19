# ibtax


## Setup
1. Get pipenv
    ```shell
    pip3 install pipx
    pipx install pdm 
    ```
2. Setup dependencies
    ```shell
    pdm install
    ``` 

## Use

1. Merge reports
    ```shell
    (cd inputs && cat \
      2018.csv \
      2019.csv \
      2020.csv \
      2021.csv \
    > report.csv)
    ```
2. Generate one
    ```shell
    pdm run ibtax --year-report inputs/report.csv
    ```
   Note, it will use the latest year available in the report(s)

