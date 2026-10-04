"""Explicitly scoped manual cloud job; does not install a recurring schedule."""
from datetime import date,datetime,timezone
from uuid import UUID
import json
import os
import sys
from app.deye_discovery import client_from_environment
from app.deye_solar_archive import archive_window
from app.deye_device_collection_service import collect_bound_device


def parse_scope(value):
    rows=json.loads(value)
    if not isinstance(rows,list) or not 1<=len(rows)<=2:
        raise ValueError('one or two explicitly selected devices required')
    result=[];seen=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'plantId','bindingId','deviceSerial'}:
            raise ValueError('explicit plant, binding and device required')
        plant=row['plantId'];serial=row['deviceSerial']
        if any(not isinstance(v,str) or not v.strip() or v!=v.strip() or len(v)>128
               for v in (plant,serial)):
            raise ValueError('invalid plant or device selection')
        binding=UUID(row['bindingId'])
        if plant in seen:raise ValueError('one selected device per plant required')
        seen.add(plant);result.append((plant,binding,serial))
    return tuple(result)


def run_job(environ,*,collector=collect_bound_device,client_factory=client_from_environment):
    scope=parse_scope(environ['HIOS_DEYE_CAPTURE_SCOPE'])
    start=date.fromisoformat(environ['HIOS_DEYE_CAPTURE_START_UTC'])
    end=date.fromisoformat(environ['HIOS_DEYE_CAPTURE_END_UTC'])
    archive_window(start,end)
    if end>=datetime.now(timezone.utc).date():raise ValueError('completed UTC days required')
    db=environ['DATABASE_URL'];subject=environ['HIOS_CAPTURE_SUBJECT'];tenant=environ['HIOS_CAPTURE_TENANT']
    if any(not isinstance(v,str) or not v.strip() for v in (db,subject,tenant)):
        raise ValueError('server scope required')
    client=client_factory();outcomes=[]
    for index,(plant,binding,serial) in enumerate(scope):
        try:
            rows=collector(db,subject,tenant_id=tenant,plant_id=plant,binding_id=binding,
                device_serial=serial,start_day=start,end_day=end,client=client)
            outcomes.append({'plantIndex':index,'days':list(rows)})
            if any(r['status']=='failed' for r in rows):break
        except Exception as error:
            outcomes.append({'plantIndex':index,'status':'failed','errorClass':type(error).__name__})
            break
    return tuple(outcomes)


def main():
    try:
        outcomes=run_job(os.environ)
        print(json.dumps({'outcomes':outcomes}))
        return int(any(o.get('status')=='failed' or any(r['status']=='failed' for r in o.get('days',[]))
                       for o in outcomes))
    except Exception as error:
        print(json.dumps({'status':'configuration_failed','errorClass':type(error).__name__}))
        return 2


if __name__=='__main__':sys.exit(main())
