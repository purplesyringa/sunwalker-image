#import <Foundation/Foundation.h>

int main(int argc, char* argv[]) {
	@autoreleasepool {
		NSString *text = @"Hello, world!\n";
		printf("%s", [text UTF8String]);
	}
}
