// SPDX-License-Identifier: GPL-2.0-or-later
/* Standard Linux I2C_RDWR and termios/TIOCM_LOOP probes. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>
#include <termios.h>
#include <sys/ioctl.h>
#include <sys/poll.h>
#ifndef TIOCM_LOOP
#define TIOCM_LOOP 0x8000 /* Linux UAPI asm-generic/termios.h */
#endif
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
int main(int argc,char **argv) {
 if(argc!=3)return 1;
 int f=open(argv[1],O_RDWR);if(f<0){perror("i2c open");return 2;}
 uint8_t v=0;struct i2c_msg m={.addr=0x7f,.len=1,.buf=&v};struct i2c_rdwr_ioctl_data d={&m,1};
 errno=0;int r=ioctl(f,I2C_RDWR,&d);printf("I2C_EMPTY_ADDRESS result=%d errno=%d\n",r,errno);
 if(r>=0 || errno!=EREMOTEIO&&errno!=ENXIO)return 3;
 puts("I2C_NACK_PROBE_PASS");
 if(getenv("I2C_EEPROM_TEST")) {
  uint8_t tx[33],rx[32],offset=0x20;for(int i=0;i<33;i++)tx[i]=i?i^0x6d:offset;
  struct i2c_msg w={.addr=0x50,.len=33,.buf=tx};d.msgs=&w;d.nmsgs=1;
  if(ioctl(f,I2C_RDWR,&d)!=1){perror("EEPROM write");return 11;}
  struct i2c_msg rd[2]={{.addr=0x50,.len=1,.buf=&offset},{.addr=0x50,.flags=I2C_M_RD,.len=32,.buf=rx}};
  d.msgs=rd;d.nmsgs=2;if(ioctl(f,I2C_RDWR,&d)!=2){perror("EEPROM read");return 12;}
  printf("I2C_EEPROM_WRITE_READ bytes=32 match=%d\n",!memcmp(tx+1,rx,32));
  if(memcmp(tx+1,rx,32))return 13;puts("I2C_EEPROM_PROBE_PASS");
 }
 close(f);
 f=open(argv[2],O_RDWR|O_NOCTTY|O_NONBLOCK);if(f<0){perror("uart open");return 4;}
 struct termios old,t;if(tcgetattr(f,&old))return 5;t=old;cfmakeraw(&t);cfsetispeed(&t,B115200);cfsetospeed(&t,B115200);t.c_cflag|=CLOCAL|CREAD;
 if(tcsetattr(f,TCSANOW,&t))return 6;
 int oldm,mc;if(ioctl(f,TIOCMGET,&oldm))return 7;mc=oldm|TIOCM_LOOP;
 if(ioctl(f,TIOCMSET,&mc))return 8;
 uint8_t tx[64],rx[64];for(int i=0;i<64;i++)tx[i]=i^0xa5;
 tcflush(f,TCIOFLUSH);if(write(f,tx,64)!=64)return 9;
 int n=0;for(int i=0;i<10&&n<64;i++){struct pollfd p={f,POLLIN,0};if(poll(&p,1,300)>0){r=read(f,rx+n,64-n);if(r>0)n+=r;}}
 ioctl(f,TIOCMSET,&oldm);tcsetattr(f,TCSANOW,&old);close(f);
 printf("UART_LOOPBACK bytes=%d match=%d\n",n,n==64&&!memcmp(tx,rx,64));
 if(n!=64||memcmp(tx,rx,64))return 10;puts("UART_LOOPBACK_PROBE_PASS");return 0;
}
