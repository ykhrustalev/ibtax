# ibtax


## Setup
1. Get pipenv
    ```shell
    pip3 install pipx
    pipx install pipenv 
    ```
2. Setup dependencies
    ```shell
    pipenv install
    ``` 

## Use

1. Merge reports
    ```shell
    cat inputs/2018.csv ... inputs/2020.csv >> inputs/report.csv  
    ```
2. Generate one
    ```shell
    pipenv run ibtaxctl --year-report inputs/report.csv
    ```
   Note, it will use the latest year available in the report(s)

