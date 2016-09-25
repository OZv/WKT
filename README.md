Copyright &copy; 2016 bt4baidu  
http://www.pdawiki.com/forum/thread-18397-1-1.html  
**敬告：本程序所产生的数据仅供个人学习之用；请勿广泛传播，请勿商用牟利。**
***  
1. 词典内嵌js脚本
--------------------
* wk.js  
联网发音及引证的显示隐藏等动态效果
2. 抓词脚本
----------------
* wkt_downloader.py  
下载及html->mdx格式转换，支持开多个进程，支持无人值守、循环检测、自动重试、断点续传
3. 用法
----------------
1. 安装python 2.7.6
2. windows下要再安装python加载器，否则弹出一堆窗口很烦人  
https://bitbucket.org/vinay.sajip/pylauncher/downloads/launcher.msi
3. 安装requests
https://pypi.python.org/pypi/requests/
4. 将wordlist.txt和wkt_downloader.py脚本文件放在同一目录下，若无wordlist.txt将自动下载生成
5. 配置下载进程数及每块的单词数，目前默认设为25个进程，每块8000个单词
      如果要修改，找到wkt_downloader.py的如下两行：  
      
                  STEP = 8000        # 每块8000个单词
                  MAX_PROCESS = 25   # 开25个进程
      进程个数的上限视个人PC的配置和网速而定，PC性能好可以开更多  
6. 打开命令行，输入py wkt_downloader.py回车运行（确保硬盘剩余容量3.5G以上）  
下载完后自动合并为单个文本文件（可直接用MdxBuilder压制成mdx词库）；  
同时生成图片目录p、v。

      参数说明：
      
                  f 	可选   仅排版转换，所有网页数据已经下载后可用
                  -l	可选   图片离线化，自动生成data目录。若不设此参数则生成在线图片版mdx
                  -q	可选   压缩png图片，需要将pngquant.exe放在此脚本同一目录下
                  -v	可选   svg图片离线化，需要事先将此脚本生成的WKT/v目录下的所有svg图片转成同名的png图片，推荐用Apache batik。
                               若不设此参数则生成在线svg图片版mdx
                  p	可选   增量更新，不可与上述参数同时设置
                  [file]	设置参数p时必选，指定用于增量更新的词汇一览表的文件名，格式参考wordlist.txt`
