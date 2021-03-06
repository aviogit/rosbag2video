#!/usr/bin/env python

"""
rosbag2video.py
rosbag to video file conversion tool 
by Maximilian Laiacker 2016
post@mlaiacker.de
"""

import roslib 
roslib.load_manifest('rosbag')
import rosbag
import sys, getopt
import os
from sensor_msgs.msg import CompressedImage
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2

import numpy as np

import shlex, subprocess

''' 
        except IOError as e:
                print("I/O error({0}): {1}".format(e.errno, e.strerror))
        except ValueError as e:
                print("Could not convert data to an integer: " . e)
        except NameError as e:
                print("NameError: ", e)
        except RuntimeError as e:
                print("RuntimeError: " . e)
        except TypeError as e:
                print("TypeError:", e)
        except CvBridgeError as e:
                print(e)
        except:
                print("Unexpected error:", sys.exc_info()[0])
                raise
'''

 
opt_fps =25.0
opt_out_file=""
opt_fourcc = "XVID"
opt_topic = ""
opt_files = []
opt_display_images = False;
def print_help():
    print
    print 'rosbag2video.py [--fps 25] [-o outputfile] [-s (show video)] [-t topic] bagfile1 [bagfile2] ...'
    print
    print 'converts image sequence(s) in ros bag file(s) to video file(s) with fixed frame rate using avconv'
    print 'avconv needs to be installed! (sudo apt-get install libav-tools)'
    print 'if no output file (-o) is given the filename \'<topic>.mp4\' is used and default output codec is h264'
    print 'multiple image topics are supportet only when -o option is _not_ used'
    print 'avconv will guess the format according to given extension'
    print 'compressed and raw image messages are supportet with mono8 and bgr8/rgb8'
    print 'Maximilian Laiacker 2016'

if len(sys.argv) < 2:
    print 'Please specify ros bag file(s)'
    print 'For example:'
    print_help()
    exit(1)
else :
   try:
      opts, opt_files = getopt.getopt(sys.argv[1:],"hsr:o:c:t:",["fps=","ofile=","codec=","topic="])
   except getopt.GetoptError:
      print_help()
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print_help()
         sys.exit()
      elif opt == '-s':
          opt_display_images = True
      elif opt in ("-r", "--fps"):
         opt_fps = float(arg)
      elif opt in ("-o", "--ofile"):
         opt_out_file = arg
      elif opt in ("-c", "--codec"):
         opt_fourcc = arg
      elif opt in ("-t", "--topic"):
         opt_topic = arg
      else:
          print "opz:", opt,'arg:', arg
         
 
def filter_image_msgs(topic, datatype, md5sum, msg_def, header):
    if(datatype=="sensor_msgs/CompressedImage"):
        if (opt_topic != "" and opt_topic == topic) or opt_topic == "":
            print "############# USING ######################" 
            print topic,' with datatype:', str(datatype)
            return True;
    if(datatype=="theora_image_transport/Packet"):
        if (opt_topic != "" and opt_topic == topic) or opt_topic == "":
            print topic,' with datatype:', str(datatype)
#            print "############# USING ######################"
            print '!!! theora not supportet, sorry !!!' 
            return False;
    if(datatype=="sensor_msgs/Image"):
        if (opt_topic != "" and opt_topic == topic) or opt_topic == "":
            print "############# USING ######################" 
            print topic,' with datatype:', str(datatype)
            return True;    
    return False;

t_first={};
t_file={};
t_video={}
cv_image = []
np_arr = []
if (opt_fps<=0):
    opt_fps = 1
print "using ",opt_fps," FPS" 

p_avconv = {}
bridge = CvBridge()

#load_flag = cv2.CV_LOAD_IMAGE_COLOR
load_flag = cv2.IMREAD_COLOR

frame_counter = 0

for files in range(0,len(opt_files)):
    #First arg is the bag to look at
    bagfile = opt_files[files]
    #Go through the bag file
    bag = rosbag.Bag(bagfile)
    for topic, msg, t in bag.read_messages(connection_filter=filter_image_msgs):
        print "frame no.:", frame_counter, topic, 'at', str(t), 'fmt:', msg.format #, 'enc:', msg.encoding #,'msg=', str(msg)
	frame_counter+=1
        try:
            if msg.format.find("jpeg")!=-1:
                if msg.format.find("8")!=-1 and (msg.format.find("rgb")!=-1 or msg.format.find("bgr")!=-1):
                    #print "rgb or bgr 8"
                    if opt_display_images:
                        np_arr = np.fromstring(msg.data, np.uint8)
                        cv_image = cv2.imdecode(np_arr, load_flag)
                        #cv_image = bridge.imgmsg_to_cv2(msg, "rgb8")
                elif msg.format.find("mono8")!=-1 :
                    #print "mono8"
                    if opt_display_images:
                        np_arr = np.fromstring(msg.data, np.uint8)
                        cv_image = cv2.imdecode(np_arr, load_flag)
                elif msg.format.find("jpeg")!=-1 :
                    #print "jpeg"
                    if opt_display_images:
                        #### direct conversion to CV2 ####
                        np_arr = np.fromstring(msg.data, np.uint8)
                        cv_image = cv2.imdecode(np_arr, load_flag) # OpenCV >= 3.0:
                else:         
                    print 'unsupported format:', msg.format
                    exit(1)
                    
                #print "len:", len(msg.data)
                if len(msg.data)>0:
                    if not topic in t_first:
                        t_first[topic] = t;
                        t_video[topic] = 0;
                        t_file[topic] = 0
                    t_file[topic] = (t-t_first[topic]).to_sec()

                    #print "t: ", t.to_sec()
                    #print "t_first:", t_first[topic].to_sec()

                    while t_video[topic]<t_file[topic]:
                        if not topic in p_avconv:
                            if opt_out_file=="":
                                out_file = str(topic).replace("/", "-")+".mp4"
                                #out_file = str(topic).replace("/", "")+".mjpeg"
                            else:
                                out_file = opt_out_file
			    print '[MJPEG] Launching AVCONV process...'
                            #subprocess.Popen(['bash','-c','echo asdfqwer qewr'])
                            #subprocess.Popen(['bash','-c','ls'])
                            #p_avconv[topic] = subprocess.Popen(['avconv','-r',str(opt_fps),'-an','-c','mjpeg','-f','mjpeg','-i','-',out_file],stdin=subprocess.PIPE)
			    extra_avconv_params="-codec:v libx264 -preset medium -crf 10 "							# This one has been used for Garda FullHD images
			    extra_avconv_params="-codec:v libx264 -preset ultrafast -crf 25 "							# This one has been used for Garda FullHD images
			    cmdline='avconv -r ' + str(opt_fps) + ' -an -c mjpeg -f mjpeg -i - ' + out_file
			    cmdline='avconv -r ' + str(opt_fps) + ' -an -c mjpeg -qscale 32 -q:v 3 -f mjpeg -i - ' + out_file
			    cmdline='avconv -r ' + str(opt_fps) + ' -an -c:v mjpeg -f mjpeg -q:v 2 -qscale 2 -b:v 65536k -i - ' + out_file
			    cmdline='ffmpeg -r ' + str(opt_fps) + ' -an -f mjpeg -i - -b:v 65536k ' + out_file # works!!!
			    cmdline='avconv -r ' + str(opt_fps) + ' -an -f mjpeg -i - -b:v 65536k ' + out_file # works!!!
			    cmdline='avconv -r ' + str(opt_fps) + ' -an -f mjpeg -i - -b:v 20480k ' + extra_avconv_params + ' ' + out_file				# This one has been used for Garda FullHD images
			    #cmdline='avconv -i - -r ' + str(opt_fps) + ' -an -c mjpeg -f mjpeg '  + extra_avconv_params + out_file
                            #size = "1920x1080"
			    #pix_fmt = "bgr24"
			    #cmdline='avconv -r ' + str(opt_fps) + ' -an -f rawvideo -s ' + size + ' -pix_fmt ' + pix_fmt + ' -i - ' + out_file
			    print 'Executing command line:', cmdline
                            p_avconv[topic] = subprocess.Popen(['bash', '-c', cmdline], stdin=subprocess.PIPE)
                        p_avconv[topic].stdin.write(msg.data)                      
                        t_video[topic] += 1.0/opt_fps
                    if opt_display_images: 
                        cv2.imshow(topic, cv_image)
                        key=cv2.waitKey(1)
                        if key==1048603:
                            exit(1);
        except AttributeError as e:
            try:
                    #print "Exception error: ", e
                    #print topic, 'at', str(t), 'fmt:', msg.format, 'enc:', msg.encoding #,'msg=', str(msg)
                    pix_fmt=""
                    if msg.encoding.find("mono8")!=-1 :
                        #print "mono8 - gray"
                        pix_fmt = "gray"
                        #np_arr = np.fromstring(msg.data, np.uint8)
                        if opt_display_images: 
                            cv_image = bridge.imgmsg_to_cv2(msg, "bgr8")
                    elif msg.encoding.find("bgr8")!=-1 :
                        #print "bgr8 - bgr24"
                        pix_fmt = "bgr24"
                        #np_arr = np.fromstring(msg.data, np.uint8)
                        if opt_display_images:
                            cv_image = bridge.imgmsg_to_cv2(msg, "bgr8")
                    elif msg.encoding.find("rgb8")!=-1 :
                        #print "rgb8 - rgb24"
                        pix_fmt = "rgb24"
                        #np_arr = np.fromstring(msg.data, np.uint8)
                        if opt_display_images:
                            cv_image = bridge.imgmsg_to_cv2(msg, "bgr8")
                    elif msg.encoding.find("jpeg")!=-1 :
                        #print "jpeg"
                        if opt_display_images:
                            #### direct conversion to CV2 ####
                            np_arr = np.fromstring(msg.data, np.uint8)
                            cv_image = cv2.imdecode(np_arr, load_flag) # OpenCV >= 3.0:
                    else:         
                        print 'unsupported encoding:', msg.encoding
                        exit(1)
                        
                    if len(msg.data)>0:                    
                        if not topic in t_first :
                            t_first[topic] = t;
                            t_video[topic] = 0;
                            t_file[topic] = 0
                        t_file[topic] = (t-t_first[topic]).to_sec()
                        while t_video[topic]<t_file[topic]:
                            if not topic in p_avconv:
                                if opt_out_file=="":
                                    out_file = str(topic).replace("/", "-")+".mp4"
                                else:
                                    out_file = opt_out_file
                                size = str(msg.width)+"x"+str(msg.height)
				print 'Launching AVCONV process...'
				extra_avconv_params=" -b 1024k -codec:v libx264 -preset medium -crf 20 "						# Low quality settings (also for Garda mjpegs)
				extra_avconv_params=" -b 65535k -codec:v libx264 -preset veryslow -crf 0 "						# This one has been used for FLIR 320x256 IR images
			        cmdline='avconv -r ' + str(opt_fps) + ' -an -f rawvideo -s ' + size + ' -pix_fmt ' + pix_fmt + ' -i - ' + out_file
				cmdline='avconv -r 30 -an -f rawvideo -s ' + size + ' -pix_fmt ' + pix_fmt + ' -i - ' + extra_avconv_params + ' ' + out_file # This one has been used for FLIR 320x256 IR images
			    	print 'Executing command line:', cmdline
                            	p_avconv[topic] = subprocess.Popen(['bash', '-c', cmdline], stdin=subprocess.PIPE)
                                #p_avconv[topic] = subprocess.Popen(['avconv','-r',str(opt_fps),'-an','-f','rawvideo','-s',size,'-pix_fmt', pix_fmt,'-i','-',out_file],stdin=subprocess.PIPE)
                                #subprocess.Popen(['bash','-c','echo','avconv','-r',str(opt_fps),'-an','-c:v','libx264','-crf','10','-vb','64k','-f','h264','-s',size,'-pix_fmt', pix_fmt,'-i','-',out_file,'>','/tmp/qwer.txt'])
                                #p_avconv[topic] = subprocess.Popen(['avconv','-r',str(opt_fps),'-an','-c:v','libx264','-crf','10','-vb','64k','-f','h264','-s',size,'-pix_fmt', pix_fmt,'-i','-',out_file],stdin=subprocess.PIPE)
                            p_avconv[topic].stdin.write(msg.data)                      
                            t_video[topic] += 1.0/opt_fps 
                        if opt_display_images:
                            cv2.imshow(topic, cv_image)
                            key=cv2.waitKey(1)
                            if key==1048603:
                                exit(1);
            except AttributeError as e:
		print "Another exception error:", e
                # maybe theora packet
                # theora not supportet
                pass 
     
    bag.close();
