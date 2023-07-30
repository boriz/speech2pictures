#/bin/bash

PID=`ps -eaf | grep ngrok | grep -v grep | awk '{print $2}'`
if [[ "" !=  "$PID" ]]; then
  echo "Killing ngrok, pid = $PID"
  kill -9 $PID
fi

PID=`ps -eaf | grep flask | grep -v grep | awk '{print $2}'`
if [[ "" !=  "$PID" ]]; then
  echo "Killing flask, pid = $PID"
  kill -9 $PID
fi


ngrok http --domain=<domain> 5000 > /dev/null &

cd ~/speach2pictures/
source ./venv/bin/activate
flask run --host=0.0.0.0 &

