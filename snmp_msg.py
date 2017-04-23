from pyasn1.codec.ber import decoder, encoder
from pysnmp.proto import api

def create():
    # Protocol version to use
    pMod = api.protoModules[api.protoVersion1]

    # Build PDU
    reqPDU = pMod.GetRequestPDU()
    pMod.apiPDU.setDefaults(reqPDU)
    pMod.apiPDU.setVarBinds(
    reqPDU, [('1.3.6.1.4.1.2435.2.3.9.1.1.7.0', pMod.Null('')),
             ('1.3.6.1.2.1.1.1.0', pMod.Null(''))]
    )

    # Build message
    reqMsg = pMod.Message()
    pMod.apiMessage.setDefaults(reqMsg)
    pMod.apiMessage.setCommunity(reqMsg, 'public')
    pMod.apiMessage.setPDU(reqMsg, reqPDU)

    #
    return encoder.encode(reqMsg)

def print_msg(wholeMsg):
    pMod = api.protoModules[api.protoVersion1]
    rspMsg, wholeMsg = decoder.decode(wholeMsg, asn1Spec=pMod.Message())
    rspPDU = pMod.apiMessage.getPDU(rspMsg)
    errorStatus = pMod.apiPDU.getErrorStatus(rspPDU)
    if errorStatus:
        print(errorStatus.prettyPrint())
    else:
        for oid, val in pMod.apiPDU.getVarBinds(rspPDU):
            print('%s = %s' % (oid.prettyPrint(), val.prettyPrint()))
