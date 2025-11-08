from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine, insert, select
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()
DB_URL = 'sqlite:///z_coba.db'

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
    added_on = Column(Float)

    HOSPITAL_AMBULANCE_ID = Column(String, ForeignKey('HOSPITAL.ID')) # FK  
    HOSPITAL_DEST_ID = Column(String, ForeignKey('HOSPITAL.ID'))  # FK
    
    


# --------------------------------- functions -------------------------------- #
### DATABASE UTILITY FUNCTIONS 
def createAllTables(engine,drop_exist=False) -> None:
    if drop_exist:
        Base.metadata.drop_all(engine)

    Base.metadata.create_all(engine)


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
    import time
    engine = create_engine(DB_URL, echo=True)
    with Session(engine) as session:
        try:
            uuid_generated = str(uuid.uuid4())

            payload = {
                "ID" : uuid_generated,
                "status" : "PREP",
                "html_fname" : f"{uuid_generated}.html",
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
        stmt = (select(PATIENT_TRANSPORT_LIST,HOSPITAL)
                .join(HOSPITAL, 
                      PATIENT_TRANSPORT_LIST.HOSPITAL_DEST_ID == HOSPITAL.ID) # find the destination hospital
                .where(PATIENT_TRANSPORT_LIST.HOSPITAL_AMBULANCE_ID == hs_id)
                )
        try:
            hospital_for_id = session.execute(select(HOSPITAL).where(HOSPITAL.ID == hs_id)).scalars().first()
            print(hospital_for_id.name)
            ret_val['hospital_name'] = hospital_for_id.name
            query_result = session.execute(stmt).all()
            for transport_detail, hospital_dest in query_result:
                ret_val['ambulance_list'].append({
                    "ID" : transport_detail.ID,
                    "status" : transport_detail.status,
                    "html_fname" : transport_detail.html_fname,
                    "hospital_dest_name" : hospital_dest.name
                })
        except Exception as e:
            print(e)
            session.rollback()
        else:
            session.commit()

    return ret_val

def getNewIncomingEmergencyPatient(hs_id):
    # PATIENT_TRANSPORT_LIST.__table__
    engine = create_engine(DB_URL, echo=True)
    ret_val = {'hospital_name': '',
               'incomingList' : []}
    with Session(engine) as session:
        stmt = (select(PATIENT_TRANSPORT_LIST)
                .join(HOSPITAL, 
                      PATIENT_TRANSPORT_LIST.HOSPITAL_AMBULANCE_ID == HOSPITAL.ID)
                .where(PATIENT_TRANSPORT_LIST.HOSPITAL_DEST_ID == hs_id))
        try:
            hospital_for_id = session.execute(select(HOSPITAL).where(HOSPITAL.ID == hs_id)).scalars().first()
            ret_val['hospital_name'] = hospital_for_id.name
            query_result = session.execute(stmt).mappings().all()
            for transport_detail, hospital_ambulance in query_result:
                ret_val['incomingList'].append({
                    "ID" : transport_detail.ID,
                    "status" : transport_detail.status,
                    "html_fname" : transport_detail.html_fname,
                    "hospital_dest_name" : hospital_ambulance.name
                })
        except:
            session.rollback()
        else:
            session.commit()

    return query_result
        


if __name__ == "__main__":
    import json     
    
    with open('hospital_seeding_data.json') as hsd:
        hospital_seeding_data = json.load(hsd)

    # print(hospital_seeding_data)
    # exit()
    
    # for i in hospital_seeding_data:
    #     print(i)

    engine = create_engine(DB_URL, echo=False)

    createAllTables(engine=engine,drop_exist=True) # recreate all table
    seedWithList(engine, HOSPITAL, hospital_seeding_data)
    # print(HOSPITAL.__table__)

