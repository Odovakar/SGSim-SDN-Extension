PROG=attack_iec104_misuse

all: $(PROG)

$(PROG): attack_iec104_misuse.c
	$(CC) -g -o $(PROG) attack_iec104_misuse.c \
	  -I../../src/inc/api -I../../src/hal/inc -I../../src/tls -I../../src/GUI \
	  ../../build/lib60870.a -lpthread

clean:
	rm -f $(PROG)
