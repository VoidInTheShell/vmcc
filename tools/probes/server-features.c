// SPDX-License-Identifier: GPL-2.0-or-later
#define _GNU_SOURCE
#include <cpuid.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>
#include <errno.h>
#include <unistd.h>
int main(void){cpu_set_t allowed,set;if(sched_getaffinity(0,sizeof(allowed),&allowed))return 2;int failed=0,count=0;
for(int cpu=0;cpu<CPU_SETSIZE;cpu++)if(CPU_ISSET(cpu,&allowed)){
 count++;CPU_ZERO(&set);CPU_SET(cpu,&set);if(sched_setaffinity(0,sizeof(set),&set))return 2;
 unsigned a,b,c,d;__cpuid_count(1,0,a,b,c,d);unsigned dca=(c>>18)&1,psn=(d>>18)&1;__cpuid_count(7,0,a,b,c,d);unsigned rdt_m=(b>>12)&1,rdt_a=(b>>15)&1,sha=(b>>29)&1,tsx=(b>>4)&1,rtm=(b>>11)&1;
 __cpuid_count(7,1,a,b,c,d);unsigned vnni=(a>>4)&1;
 printf("CPU %d: DCA=%u PSN=%u RDT_MON=%u RDT_ALLOC=%u HLE=%u RTM=%u SHA=%u AVX_VNNI=%u\n",cpu,dca,psn,rdt_m,rdt_a,tsx,rtm,sha,vnni);failed|=dca|psn|rdt_m|rdt_a|tsx|rtm;
 for(unsigned leaf=0xf;leaf<=0x10;leaf++)for(unsigned sub=0;sub<=3;sub++){__cpuid_count(leaf,sub,a,b,c,d);printf("CPU %d CPUID %02x.%u: %08x %08x %08x %08x\n",cpu,leaf,sub,a,b,c,d);failed|=(a|b|c|d)!=0;}
 char path[80];snprintf(path,sizeof(path),"/dev/cpu/%d/msr",cpu);int fd=open(path,O_RDONLY);
 if(fd<0){printf("CPU %d MSR unavailable: %s\n",cpu,strerror(errno));failed=1;continue;}
 const unsigned msrs[]={0x4e,0x4f,0xc8d,0xc8e,0xc8f,0xc90};for(unsigned k=0;k<sizeof(msrs)/sizeof(msrs[0]);k++){uint64_t v=0;errno=0;ssize_t n=pread(fd,&v,8,msrs[k]);printf("CPU %d MSR %04x: %s value=%016llx errno=%d\n",cpu,msrs[k],n==8?"READABLE":"UNSUPPORTED",(unsigned long long)v,errno);if(n==8)failed=1;}
 close(fd);
}
if(count!=24)failed=1;printf("TESTED_VCPUS=%d\nSERVER_FEATURE_AUDIT=%s\n",count,failed?"FAIL":"PASS");return failed;
}
