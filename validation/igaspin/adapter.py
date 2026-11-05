"""Conditional wire-order adapter; ordinal identity is not verified band identity."""
import calendar,datetime,struct
NS=1_000_000_000

def frames(data):
 i=0
 while i<len(data):
  if data[i:i+2]==b'\xb5\x62':
   if i+6>len(data):raise ValueError('truncated header')
   c,m,n=struct.unpack_from('<BBH',data,i+2);end=i+8+n
   if end>len(data):raise ValueError('truncated UBX')
   a=b=0
   for x in data[i+2:end-2]:a=(a+x)&255;b=(b+a)&255
   if data[end-2:end]!=bytes([a,b]):raise ValueError('UBX checksum')
   yield i,end,c,m,data[i+6:end-2];i=end
  elif data[i:i+1]==b'$':
   end=data.find(b'\r\n',i)
   if end<0:raise ValueError('NMEA truncation')
   line=data[i:end];body,check=line[1:].rsplit(b'*',1);v=0
   for x in body:v^=x
   if len(check)!=2 or int(check,16)!=v:raise ValueError('NMEA checksum')
   i=end+2
  else:raise ValueError('unexplained byte at '+str(i))

def nav(p):
 if len(p)!=92:return None
 year=struct.unpack_from('<H',p,4)[0];utc=None
 if p[11]&3==3:
  try:utc=calendar.timegm(datetime.datetime(year,*p[6:11]).timetuple())*NS+struct.unpack_from('<i',p,16)[0]
  except ValueError:pass
 return {'utc_ns':utc,'iTOW_ms':struct.unpack_from('<I',p)[0],'tAcc_ns':struct.unpack_from('<I',p,12)[0],'eph':struct.unpack_from('<I',p,40)[0]/1000,'epv':struct.unpack_from('<I',p,44)[0]/1000}

def observations(data):
 prev_end=None;last_time=None;bucket=[];origin=None
 for start,end,c,m,p in frames(data):
  if (c,m)==(10,56):bucket.append((start,end,p))
  if (c,m)!=(1,7):continue
  n=nav(p)
  if n is None:raise ValueError('unsupported NAV-PVT shape')
  if n['utc_ns'] is None:raise ValueError('invalid NAV time; prereplay clock integrity failure')
  if last_time is not None and n['utc_ns']<=last_time:raise ValueError('nonmonotonic UTC')
  if origin is None:origin=n['utc_ns']
  reason=None;rf=None
  eligible=[x for x in bucket if prev_end is not None and x[0]>=prev_end and x[1]<=start]
  if prev_end is None:reason='first_NAV_without_previous_anchor'
  elif len(eligible)!=1:reason='fresh_RF_count_'+str(len(eligible))
  else:
   rf=eligible[0];q=rf[2]
   if len(q)!=52 or q[0]!=0 or q[1]!=2:reason='unsupported_RF_shape'
  arms=[]
  for ordinal in [0,1]:
   q=rf[2] if rf else None
   arms.append({'arm':f'rf_ordinal_{ordinal}','available':reason is None,'unavailable_reason':reason,'rf_offset':None if rf is None else rf[0],'rf_end_exclusive':None if rf is None else rf[1],'rf_ordinal':ordinal,'literal_blockId':None if reason else q[4+24*ordinal],'noise_per_ms':None if reason else struct.unpack_from('<H',q,16+24*ordinal)[0]})
  yield {**n,'nav_offset':start,'nav_end_exclusive':end,'previous_nav_end_exclusive':prev_end,'elapsed_s':(n['utc_ns']-origin)/NS,'fresh_RF_count':len(eligible),'arms':arms,'physical_RF_age_s':None,'same_receiver_epoch_verified':False}
  prev_end=end;last_time=n['utc_ns'];bucket=[]

def new_event_delays_ns(events,reference_ns,deadline_s):
 return [e-reference_ns for e in events if reference_ns<=e<=reference_ns+deadline_s*NS]
