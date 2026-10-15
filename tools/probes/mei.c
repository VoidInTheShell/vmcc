// SPDX-License-Identifier: GPL-2.0-or-later
/* Standard Linux MEI ioctl + MKHI request probe; no driver changes. */
#include <stdio.h>
#include <stdint.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/poll.h>
#include <linux/mei.h>
int main(void) {
 int fd=open("/dev/mei0",O_RDWR); if(fd<0){perror("mei open");return 1;}
 struct mei_connect_client_data c={0};
 const uint8_t uuid[]={0x84,0x35,0x21,0x55,0x29,0x9a,0x16,0x49,0xba,0xdf,0x0f,0xb7,0xed,0x68,0x2a,0xeb};
 for(int i=0;i<16;i++)c.in_client_uuid.b[i]=uuid[i];
 if(ioctl(fd,IOCTL_MEI_CONNECT_CLIENT,&c)<0){perror("mei connect");return 2;}
 printf("MEI_CONNECT mtu=%u protocol=%u\n",c.out_client_properties.max_msg_length,c.out_client_properties.protocol_version);
 for(int i=0;i<8;i++) {
  uint8_t req[]={0xff,2,0,0},buf[256];
  if(write(fd,req,4)!=4){perror("mei write");return 3;}
  struct pollfd p={fd,POLLIN,0};if(poll(&p,1,3000)<=0){perror("mei poll");return 4;}
  int n=read(fd,buf,sizeof(buf));printf("MKHI_REPLY_%d len=%d bytes=",i,n);
  for(int j=0;j<n;j++)printf("%02x",buf[j]);puts("");
  if(n!=12||buf[0]!=0xff||buf[1]!=0x82||buf[3])return 5;
  printf("ME_VERSION=%u.%u.%u.%u\n",buf[6],buf[4]|buf[5]<<8,buf[10]|buf[11]<<8,buf[8]|buf[9]<<8);
 }
 close(fd);puts("MEI_MKHI_PROBE_PASS");return 0;
}
