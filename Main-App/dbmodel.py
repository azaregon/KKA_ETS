from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine, insert, select
from sqlalchemy.orm import declarative_base, Session, aliased
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()
DB_URL = 'sqlite:///z_coba.db'

class USER(Base,UserMixin):
    __tablename__ = 'USER'
    ID = Column(String(20),primary_key=True)
    name = Column(String)
    password = Column(String)
    role = Column(String(10)) # RSADMIN, DRIVER, HEAD, APPADMIN 
    RSID = Column(Integer)


    def setPassword(self, new_password):
        self.password = generate_password_hash(new_password)

    def checkPassword(self, input_password):
        self.password = check_password_hash(input_password)


class HOSPITAL(Base):
    __tablename__ = 'HOSPITAL'
    ID = Column(Integer, primary_key=True)
    name = Column(String)
    x = Column(Float)
    y = Column(Float)
    load_percentage = Column(Integer)
    wait_time = Column(Float)
    

class PATIENT_TRANSPORT_LIST(Base):
    __tablename__ = 'PATIENT_TRANSPORT_LIST'
    ID = Column(String, primary_key=True)
    status = Column(String) # PREP, TO_PATIENT, TO_HOSPITAL, AT_HOSPITAL, ON_MISSON, AT
    html_fname = Column(String)
    audio_note_fname = Column(String)
    added_on = Column(Float)

    HOSPITAL_AMBULANCE_ID = Column(String, ForeignKey('HOSPITAL.ID')) # FK  
    HOSPITAL_DEST_ID = Column(String, ForeignKey('HOSPITAL.ID'))  # FK
    
    


# --------------------------------- functions -------------------------------- #
from datetime import datetime
import time


### DATABASE UTILITY FUNCTIONS 
def createAllTables(engine,drop_exist=False) -> None:
    if drop_exist:
        Base.metadata.drop_all(engine)

    Base.metadata.create_all(engine)


def dropTable(engine,table_class):
    table_class.__table__.drop(engine)

def createTable(engine,table_class):
    table_class.__table__.create(engine)


def seedWithList(engine, table_class, seed_list):
    with Session(engine) as session:
        try:
            session.execute(insert(table_class.__table__), seed_list)
        except:
            session.rollback()
        session.commit()


### DATABASE REAL USE FUNCTION

def addNewpatientTransportRecord(hs_id_from,hs_id_to):

    import uuid
    
    engine = create_engine(DB_URL, echo=True)
    with Session(engine) as session:
        try:
            uuid_generated = str(uuid.uuid4())

            payload = {
                "ID" : uuid_generated,
                "status" : "PREP",
                "html_fname" : f"{uuid_generated}.html",
                "audio_note_fname" : f"{uuid_generated}.webm",
                "added_on" : time.time(),

                "HOSPITAL_AMBULANCE_ID" : str(hs_id_from),
                "HOSPITAL_DEST_ID" : str(hs_id_to)

            }

            session.execute(insert(PATIENT_TRANSPORT_LIST.__table__), payload)
            session.commit()
        except:
            session.rollback()
            raise

        return payload


def getAllAmbulanceRequest(hs_id):
    # PATIENT_TRANSPORT_LIST.__table__
    engine = create_engine(DB_URL, echo=True)
    ret_val = {'hospital_name': '',
               'ambulance_list' : []}
    with Session(engine) as session:
        stmt = (select(PATIENT_TRANSPORT_LIST, HOSPITAL)
                .join(HOSPITAL, 
                      PATIENT_TRANSPORT_LIST.HOSPITAL_DEST_ID == HOSPITAL.ID) # find the destination hospital
                .where(PATIENT_TRANSPORT_LIST.HOSPITAL_AMBULANCE_ID == hs_id)
                .order_by(PATIENT_TRANSPORT_LIST.added_on)
                )
        try:
            hospital_for_id = session.execute(select(HOSPITAL).where(HOSPITAL.ID == hs_id)).scalars().first()
            # print(hospital_for_id.name)      
            ret_val['hospital_name'] = hospital_for_id.name
            query_result = session.execute(stmt).all()
            for transport_detail, hospital_dest in query_result:
                ret_val['ambulance_list'].append({
                    "ID" : transport_detail.ID,
                    "added_on" : datetime.fromtimestamp(transport_detail.added_on).strftime('%Y-%m-%d %H:%M:%S'), 
                    "status" : transport_detail.status,
                    "html_fname" : transport_detail.html_fname,
                    "hospital_dest_name" : hospital_dest.name
                })
        except Exception as e:
            # print(e)
            session.rollback()
        else:
            session.commit()

    return ret_val

def getAllIncomingEmergencyPatient(hs_id):
    # PATIENT_TRANSPORT_LIST.__table__
    engine = create_engine(DB_URL, echo=True)
    ret_val = {'hospital_name': '',
               'incoming_list' : []}
    with Session(engine) as session:
        # stmt = (select(PATIENT_TRANSPORT_LIST,HOSPITAL)
        #         .join(HOSPITAL, 
        #               PATIENT_TRANSPORT_LIST.HOSPITAL_AMBULANCE_ID == HOSPITAL.ID)
        #         .where(PATIENT_TRANSPORT_LIST.HOSPITAL_DEST_ID == hs_id))
        stmt = (select(PATIENT_TRANSPORT_LIST,HOSPITAL)
                .join(HOSPITAL, 
                      PATIENT_TRANSPORT_LIST.HOSPITAL_AMBULANCE_ID == HOSPITAL.ID) # find the destination hospital
                .where(PATIENT_TRANSPORT_LIST.HOSPITAL_DEST_ID == hs_id)
                .order_by(PATIENT_TRANSPORT_LIST.added_on)

                )
        try:
            hospital_for_id = session.execute(select(HOSPITAL).where(HOSPITAL.ID == hs_id)).scalars().first()
            ret_val['hospital_name'] = hospital_for_id.name
            query_result = session.execute(stmt).all()
            for transport_detail, hospital_dest in query_result:
                # print()
                # print(query_result)
                # print()
                ret_val['incoming_list'].append({
                    "ID" : transport_detail.ID,
                    "added_on" : datetime.fromtimestamp(transport_detail.added_on).strftime('%Y-%m-%d %H:%M:%S'), 
                    "status" : transport_detail.status,
                    "html_fname" : transport_detail.html_fname,
                    "hospital_dest_name" : hospital_dest.name
                })
        except Exception as e:
            # print()
            # print(e)
            # print()
            session.rollback()
        else:
            session.commit()

    return ret_val

def getReport(map_id):
    # PATIENT_TRANSPORT_LIST.__table__
    engine = create_engine(DB_URL, echo=True)
    ret_val = { 'ID' : '',
                'status' : '', # PREP, TO_PATIENT, TO_HOSPITAL, AT_HOSPITAL, ON_MISSON, AT
                'html_fname' : '',
                'audio_note_fname' : '',
                'added_on' : ''}
    with Session(engine) as session:
        hospital_ambulance = aliased(HOSPITAL)
        hospital_dest = aliased(HOSPITAL)

        stmt = (
            select(PATIENT_TRANSPORT_LIST,hospital_ambulance,hospital_dest)
            .join(hospital_ambulance, PATIENT_TRANSPORT_LIST.HOSPITAL_AMBULANCE_ID == hospital_ambulance.ID)
            .join(hospital_dest, PATIENT_TRANSPORT_LIST.HOSPITAL_DEST_ID == hospital_dest.ID)
            .where(PATIENT_TRANSPORT_LIST.ID == map_id)
        )
        try:
            # hospital_for_id = session.execute(select(HOSPITAL).where(HOSPITAL.ID == hs_id)).scalars().first()
            # ret_val['hospital_name'] = hospital_for_id.name
            report, hs_ambulance, hs_dest = session.execute(stmt).first()
            print()
            # print(query_result)
            print()
            ret_val = { 
                'ID' : report.ID,
                'status' : report.status, # PREP, TO_PATIENT, TO_HOSPITAL, AT_HOSPITAL, ON_MISSON, AT
                'html_fname' : report.html_fname,
                'audio_note_fname' : report.audio_note_fname,
                'added_on' : datetime.fromtimestamp(report.added_on).strftime('%Y-%m-%d %H:%M:%S'),
                'hospital_ambulance' : hs_ambulance.name,
                'hospital_dest' : hs_dest.name
            }
        except Exception as e:
            print()
            # print(e)
            print()
            session.rollback()
        else:
            session.commit()

    return ret_val
    
        


if __name__ == "__main__":
    import json     
    
    with open('hospital_seeding_data.json') as hsd:
        hospital_seeding_data = json.load(hsd)

    # print(hospital_seeding_data)
    # exit()
    
    # for i in hospital_seeding_data:
    #     print(i)

    engine = create_engine(DB_URL, echo=False)

    # dropTable(engine,USER)
    # createTable(engine,USER)
    createAllTables(engine=engine,drop_exist=True) # recreate all table
    seedWithList(engine, HOSPITAL, hospital_seeding_data)
    exit()
    createAllTables(engine=engine,drop_exist=False) # recreate all table
    # print(HOSPITAL.__table__)

