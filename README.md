Agora criamos o txt asssim: (para o scan.sh)
IP:porta

versao.py: Vai ler o txt de IP:porta...e retornar modelo, firmware, sendo possível filtrar se é MHDX BR.
COMANDO: python3 versao.py -f ips37777.txt -t 300 -o intelversao1.csv

dh.py: Para trabalhar junto depois de filtrado pra varias portas diferentes.

grep "MHDX" resultado.csv | cut -d',' -f1 > /home/ubuntu/VersaoDH/mhdx_alvos.txt

COMANDO: python3 dh.py -f /home/ubuntu/VersaoDH/mhdx_alvos.txt -u pdr -P Senha@2026 -t 50

DEFINITIVO ATÉ O MOMENTO: python3 dh.py -f /home/ubuntu/VersaoDH/ips37777.txt -u pdr -P Senha@2026 -t 50

Basicamente, você com o scan.sh escaneia o range em várias portas 80,37777,9090,8080
Depois com o versao.py ele vai atras dos MHDX...
Quando você tiver o resultado dos MHDX, pega a lista de IPS:porta, e cola nos IPS37777.TXT....E roda o dh...


:IMPORTANTE:

python3 dh.py -f todos_ips.txt -t 50 -p 37777

================================================

sudo masscan -p 37777 179.100.0.0-179.120.255.254 --rate 5000 -oL /home/ubuntu/VersaoDH/ips_encontrados.txt -e ens5

================================================

grep 'open tcp 37777' /home/ubuntu/VersaoDH/ips_encontrados.txt | awk '{print $4}' > /home/ubuntu/VersaoDH/ipsformatados.txt

================================================

python3 versaov2.py -f ipsformatados.txt -p 8080

================================================

python3 dh.py -f /home/ubuntu/VersaoDH/mhdx_alvos.txt -u pdr -P Senha@2026 -t 50

================================================

tail -n +2 resultado.csv | cut -d',' -f1 > todos_ips.txt

=================================================

python3 dh.py -f /home/ubuntu/VersaoDH/todos_ip.txt -u pdr -P Senha@2026 -t 50
