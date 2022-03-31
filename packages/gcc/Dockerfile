FROM gcc:latest

# Precompile bits/stdc++.h -- a commonly included header. It has to be compiled with the same flags
# as the file it'll be used with, so we compile it for all standards.
RUN \
	for version in 11 14 17 20; do \
		mkdir "/usr/local/include/c++$version" && \
		mkdir "/usr/local/include/c++$version/bits" && \
		g++ /usr/local/include/c++/*/x86_64-linux-gnu/bits/stdc++.h "-std=c++$version" -O2 -g && \
		mv "$(echo /usr/local/include/c++/*/x86_64-linux-gnu)/bits/stdc++.h.gch" "/usr/local/include/c++$version/bits/stdc++.h.gch"; \
	done
