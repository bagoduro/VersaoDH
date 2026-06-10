Agora criamos o txt asssim: (para o scan.sh)
IP:porta

versao.py: Vai ler o txt de IP:porta...e retornar modelo, firmware, sendo possível filtrar se é MHDX BR.
COMANDO: python3 versao.py -f ips37777.txt -t 300 -o intelversao1.csv

dh.py: Para trabalhar junto depois de filtrado pra varias portas diferentes.

grep "MHDX" resultado.csv | cut -d',' -f1 > /home/ubuntu/DahuaConsole/mhdx_alvos.txt

COMANDO: python3 dh.py -f /home/ubuntu/DahuaConsole/mhdx_alvos.txt -u pdr -P Senha@2026 -t 50

DEFINITIVO ATÉ O MOMENTO: python3 dh.py -f /home/ubuntu/DahuaConsole/ips37777.txt -u pdr -P Senha@2026 -t 50

Basicamente, você com o scan.sh escaneia o range em várias portas 80,37777,9090,8080
Depois com o versao.py ele vai atras dos MHDX...
Quando você tiver o resultado dos MHDX, pega a lista de IPS:porta, e cola nos IPS37777.TXT....E roda o dh...
