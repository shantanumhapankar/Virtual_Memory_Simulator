#!/usr/bin/env python

import sys
import argparse
from time import sleep

class RAM():
    def __init__(self,numofframes):
        self.numofframes = numofframes
        self.framecount = 0
        self.ram = {}
        self.lru = {}

    def check(self):
        if self.framecount >= self.numofframes:
            return 0
        else:
            return 1

    def add(self, pageentry):
        self.ram[self.framecount] = pageentry
        self.lru[self.framecount] = 0
        for i in range(len(self.lru)):
            self.lru[i] += 1
        pageentry.ramframe = self.framecount
        pageentry.add()
        self.framecount += 1
        pageentry.dirty = 0

    def replace(self, pageentry):
        replacementframe = {}
        maxlrucount = 0
        for i in range(len(self.lru)):
            if self.lru[i] > maxlrucount:
                maxlrucount = self.lru[i]
                replacementframe = self.ram[i]
        self.ram[replacementframe.ramframe] = pageentry
        self.lru[replacementframe.ramframe] = 0
        pageentry.ramframe = replacementframe.ramframe
        pageentry.add()
        pageentry.dirty = 0
        for i in range(len(self.lru)):
            self.lru[i] += 1
        replacementframe.replace()

    def update(self, pageentry):
        self.lru[pageentry.ramframe] = 0
        for i in range(len(self.lru)):
            self.lru[i] += 1
        self.ram[pageentry.ramframe] = pageentry
        pageentry.add()
        pageentry.dirty = 0


class PageTableEntry():
    def __init__(self):
        self.dirty = 0
        self.valid = 0
        self.ramframe = -1

    def checkoffset(self, offset):
        return hex(offset)

    def add(self):
        self.valid = 1

    def replace(self):
        self.dirty = 0
        self.valid = 0
        self.ramframe = -1

    def write(self):
        self.dirty = 1
   

class TLB():
    def __init__(self, tlbsize, policy):
        self.tlb = []
        self.dirty = 0
        self.tlbsize = tlbsize
        self.policy = policy

    def checkstatus(self, vpagenum):
        self.flag = 0
        for tlbe in self.tlb:
            if vpagenum in tlbe:
                self.flag = 1
                if self.policy == "lru":
                    tlbe["count"] = 0
                    for i in self.tlb:
                        i["count"] += 1
                return self.flag           
            else:
                self.flag = 0

        if self.policy == "lru":
            for i in self.tlb:
                i["count"] += 1

        return self.flag

    def add(self, vpagenum):
        fiforeplaceentry = {}
        maxlrucount = 0
        if self.policy == "lru":
            if len(self.tlb) >= self.tlbsize:
                for tlbe in self.tlb:
                    if tlbe["count"] > maxlrucount:
                        maxlrucount = tlbe["count"]
                        lrureplaceentry = tlbe

                for i in xrange(len(self.tlb)):
                    if self.tlb[i] == lrureplaceentry:
                        self.tlb[i] = {vpagenum: "1", "count": 0}

            else:
                self.tlb.append({vpagenum: "1", "count": 0})

        if self.policy == "fifo":
            if len(self.tlb) >= self.tlbsize:
                for tlbe in self.tlb:
                    if tlbe["count"] == 0:
                        fiforeplaceentry = tlbe

                for tlbe in self.tlb:
                    tlbe["count"] -= 1

                for i in xrange(len(self.tlb)):
                    if self.tlb[i] == fiforeplaceentry:
                        self.tlb[i] = {vpagenum: "1", "count": self.tlbsize}

            else:
                self.tlb.append({vpagenum: "1", "count": len(self.tlb)})


def main():
    parser = argparse.ArgumentParser(description='Simple VM Simulator.')
    parser.add_argument("-f", required=True, help="Trace File")
    parser.add_argument("-tp", required=True, help="Replacement Policy for TLB - LRU or FIFO")
    parser.add_argument("-pp", required=True, help="Replacement Policy for Page - LRU")
    parser.add_argument("-psize", required=True, help="Page Size")
    parser.add_argument("-tsize", required=True, help="TLB Entries")
    parser.add_argument("-ramsize", required=True, help="RAM Size(num of bits)")

    totalmemaccesses = 0
    totalpagefaults = 0
    totaltlbmisses = 0
    totalinst = 0

    args = parser.parse_args()
    filename = args.f
    ramsize = int(args.ramsize)
    policy = args.tp
    pagesize = int(args.psize) - 1
    offsetbits =  pagesize.bit_length()
    tlbsize = int(args.tsize)
    pte = [PageTableEntry() for i in range(pow(2,(32-offsetbits)))]
    numofframes = pow(2,(ramsize-offsetbits))
    ram = RAM(numofframes)
    tlb = TLB(tlbsize, policy)
    
    total_accesses = 0
    print "-------------------------------------------------"
    print "**************Starting VM Simulation*************"
    with open(filename, 'rb') as tracefile:
        for line in tracefile:
            totalinst += 1
            totalmemaccesses += 1
            linedata = line.split()
            address = int(linedata[0], 16)  
            operation = linedata[1]
            vpagenum = (address >> offsetbits)
            offset = address & pagesize
            tlbstatus = tlb.checkstatus(vpagenum)

            # print hex(address), hex(vpagenum), hex(pagesize), hex(offset), tlbstatus

            if tlbstatus is not 1:
                totalmemaccesses += 1
                totaltlbmisses += 1
                if pte[vpagenum].valid:
                    # print "valid"
                    if operation is 'W':
                        pte[vpagenum].write()
                    ram.update(pte[vpagenum])

                else:
                    # print "invalid"
                    totalmemaccesses += 1
                    totalpagefaults += 1
                    if(ram.check()):
                        # print "pass"
                        if operation is 'W':
                            pte[vpagenum].write()
                        ram.add(pte[vpagenum])
                    else:
                        ram.replace(pte[vpagenum])

                tlb.add(vpagenum)

            # else:
            #     pass

    print "Replacement policy used -", policy
    print "Total Virtual Addresses in the trace file -", totalinst
    print "Total Memory Accesses -", float(totalmemaccesses)/totalinst
    print "Total Page Faults -", totalpagefaults
    print "Page Fault % - ", (float(totalpagefaults)/totalinst) * 100
    print "Total TLB Misses -", totaltlbmisses
    print "TLB Miss % - ", (float(totaltlbmisses)/totalinst) * 100
    print "-------------------------------------------------"

if __name__ == "__main__":
    main()
