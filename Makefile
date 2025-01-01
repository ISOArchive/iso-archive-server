create_venv:
	python3 -m venv venv
	. venv/bin/activate; pip install -U pip wheel setuptools
	. venv/bin/activate; pip install -U -r requirements.txt

activate_venv:
	. venv/bin/activate

run_fastapi:
	. venv/bin/activate; fastapi run --reload

run_fastapi_dev:
	. venv/bin/activate; fastapi dev

screen_start:
	screen -dmS fastapi sh -c '. venv/bin/activate; fastapi run --reload'
	screen -dmS fastapi_pull sh -c 'watch -n 10 git pull'

screen_stop:
	screen -S fastapi -X quit
	screen -S fastapi_pull -X quit

screen_running:
	printf "\nThere is a screen on:\n"; screen -ls | grep fastapi

screen_ls:
	printf "\nThere is a screen on:\n"; screen -ls | grep fastapi

screen_attach:
	screen -r fastapi
