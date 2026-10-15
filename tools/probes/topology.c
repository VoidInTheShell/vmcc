// SPDX-License-Identifier: GPL-2.0-or-later
#define _GNU_SOURCE
#include <cpuid.h>
#include <sched.h>
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
int main(void) {
 cpu_set_t allowed,set; int pc=0,ec=0,total=0,failed=0;
 if(sched_getaffinity(0,sizeof allowed,&allowed)) return 2;
 for(int cpu=0;cpu<CPU_SETSIZE;cpu++) if(CPU_ISSET(cpu,&allowed)) {
  CPU_ZERO(&set); CPU_SET(cpu,&set);
  if(sched_setaffinity(0,sizeof set,&set)) return 2;
  unsigned a,b,c,d,apic,ct;
  __cpuid_count(1,0,a,b,c,d);apic=b>>24;failed|=a!=0xb0671 || (c>>31)!=0;
  __cpuid_count(0x1a,0,a,b,c,d);ct=a>>24;
  if(ct==0x40) pc++;else if(ct==0x20)ec++;else failed=1;
  printf("CPU %02d: core_type=0x%02x APIC=%02u",cpu,ct,apic);
  for(unsigned leaf=0xb;leaf<=0x1f;leaf+=0x14) {
   __cpuid_count(leaf,0,a,b,c,d);
   printf(" leaf%02x.SMT=%u",leaf,b);failed|=b!=1 || a!=0;
   __cpuid_count(leaf,1,a,b,c,d);
   printf(" leaf%02x.PKG=%u",leaf,b);failed|=b!=24 || a!=6;
  }
  __cpuid_count(4,2,a,b,c,d);
  unsigned size=((b&4095)+1)*(((b>>12)&1023)+1)*((b>>22)+1)*(c+1);
  unsigned share=((a>>14)&4095)+1;
  printf(" L2=%u L2_ID=%u L2_SHARING=%u\n",size,apic/(ct==0x40?1:4),share);
  failed |=size!=(ct==0x40?2:4)*1024*1024 || share!=(ct==0x40?1:4);
  failed |=apic!=(unsigned)(cpu<8?cpu:cpu+24);
  total++;
 }
 printf("P_CORES=%d\nE_CORES=%d\nTOTAL_CORES=%d\nTHREADS_PER_CORE=1\n",pc,ec,total);
 failed|=pc!=8||ec!=16||total!=24;
 printf("HYBRID_TOPOLOGY_AUDIT=%s\n",failed?"FAIL":"PASS");return failed;
}
