"""Collect missing days in a bounded closed UTC window for two pilot devices."""
import os,json,math,sys
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import psycopg
from app.deye_openapi import DeyeReadOnlyClient,DeyeCredentials
from app.deye_dashboard_binding import SERVER_CREDENTIAL_REFERENCE
from app.deye_device_collection_service import collect_bound_device

_FAILURE_STAGES = {
 '/v1.0/account/token': 'authentication',
 '/v1.0/station/list': 'station_discovery',
 '/v1.0/station/device': 'device_membership',
 '/v1.0/device/latest': 'measurement_discovery',
 '/v1.0/device/historyRaw': 'history_read',
}

def collection_window(now, lookback):
 if now.tzinfo is None or now.utcoffset() is None:
  raise ValueError('aware collection time required')
 if not isinstance(lookback,str) or not lookback.isascii() or not lookback.isdecimal():
  raise ValueError('integer lookback required')
 days=int(lookback)
 if not 1<=days<=31:raise ValueError('lookback must be 1..31 completed days')
 end=now.astimezone(timezone.utc).date()-timedelta(days=1)
 return end-timedelta(days=days-1),end

def main():
 start_day,end_day=collection_window(datetime.now(timezone.utc),os.environ.get('HIOS_DEYE_LOOKBACK_DAYS','7'))
 db=os.environ['DATABASE_URL'];subject=os.environ['HIOS_CAPTURE_SUBJECT'];tenant=os.environ['HIOS_CAPTURE_TENANT']
 ids=json.loads(os.environ['HIOS_CAPTURE_PLANTS'])
 if not isinstance(ids,list) or len(ids)!=2 or len(set(ids))!=2:raise ValueError('two scoped plants required')
 api=DeyeReadOnlyClient(DeyeCredentials(*(os.environ[k] for k in ('DEYE_APP_ID','DEYE_APP_SECRET','DEYE_ACCOUNT_EMAIL','DEYE_ACCOUNT_PASSWORD'))))
 token=api.obtain_token()
 class Cached:
  def obtain_token(self):return token
  def __getattr__(self,name):return getattr(api,name)
 client=Cached();body=api.list_stations(token,page=1,size=100);data=body.get('data',body)
 stations=data if isinstance(data,list) else data.get('records',data.get('list',data.get('stationList',[])))
 if not isinstance(stations,list) or len(stations)>=100:raise ValueError('bounded station list required')
 specs=[('Погреби',50.54085,30.626047222222),('Борщів',50.301388888889,31.312091666667)];plans=[]
 for ordinal,(plant,spec) in enumerate(zip(ids,specs)):
  prefix,lat,lon=spec
  with psycopg.connect(db,connect_timeout=5) as connection:
   profile=connection.execute('SELECT pp.latitude,pp.longitude FROM plant p JOIN plant_profile pp ON pp.plant_id=p.public_id JOIN membership m ON m.tenant_id=p.tenant_id WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active',(tenant,plant,subject)).fetchone()
   if not profile or not math.isclose(float(profile[0]),lat,abs_tol=1e-8) or not math.isclose(float(profile[1]),lon,abs_tol=1e-8):raise ValueError('pilot coordinates not confirmed')
   hashes={r[0] for r in connection.execute('SELECT DISTINCT device_sha256 FROM device_solar_capture WHERE tenant_id=%s AND plant_id=%s',(tenant,plant))}
  matches=[s for s in stations if str(s.get('stationName',s.get('name',''))).strip().casefold().startswith(prefix.casefold())]
  if len(matches)!=1:raise ValueError('ambiguous station')
  station=matches[0].get('stationId',matches[0].get('id'))
  if not isinstance(station,int) or isinstance(station,bool) or station<=0:raise ValueError('invalid station')
  devices=api.station_devices(token,(station,),size=100).get('deviceListItems')
  if not isinstance(devices,list) or not devices or len(devices)>=100:raise ValueError('bounded devices required')
  serials=[d['deviceSn'] for d in devices]
  latest=api.device_latest(token,tuple(serials))
  supported=[d['deviceSn'] for d in latest['deviceDataList'] if any(v.get('key')=='TotalSolarPower' and v.get('unit')=='W' for v in d.get('dataList',[]))]
  if len(supported)!=1 or hashes!={sha256(supported[0].encode()).hexdigest()}:raise ValueError('existing device lineage mismatch')
  plans.append((ordinal,plant,station,supported[0]))
 for ordinal,plant,station,serial in plans:
  with psycopg.connect(db,connect_timeout=5) as connection:
   rows=connection.execute("SELECT binding_id FROM inverter_cloud_binding WHERE tenant_id=%s AND plant_id=%s AND provider='deye_cloud' AND external_plant_id=%s AND credential_reference=%s AND discovery_status='verified' AND read_only",(tenant,plant,str(station),SERVER_CREDENTIAL_REFERENCE)).fetchall()
  if len(rows)!=1:raise PermissionError('unique verified binding required')
  binding=rows[0][0]
  outcomes=collect_bound_device(db,subject,tenant_id=tenant,plant_id=plant,binding_id=binding,device_serial=serial,start_day=start_day,end_day=end_day,client=client)
  print(json.dumps({'outcome':'bounded_collection','plantIndex':ordinal,'verified':'verified','days':outcomes}),flush=True)
  if any(o['status']=='failed' for o in outcomes):return 1
 return 0
def run():
 try:return main()
 except Exception as error:
  endpoint=getattr(error,'endpoint',None)
  stage=_FAILURE_STAGES.get(endpoint,'unknown') if isinstance(endpoint,str) else 'unknown'
  print(json.dumps({'outcome':'collection_failed','errorClass':type(error).__name__,'providerCode':getattr(error,'provider_code',None),'stage':stage}),flush=True)
  return 1

if __name__=='__main__':
 sys.exit(run())
