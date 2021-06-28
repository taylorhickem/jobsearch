// project: applicationTrackingApp
// declarations
var ss = SpreadsheetApp.getActiveSpreadsheet();
var log_sht = ss.getSheetByName("logsheet");
var steps_sht = ss.getSheetByName("steps");
var rcd_sht = ss.getSheetByName("sessions");

// column field offsets in user form
var stepOffset = 1;              // stepid field
var commentOffset = 3;           // comment field
var startOffset = 4;             // start time field
var userCol = [stepOffset,commentOffset,
    startOffset,startOffset+1];  // all user input fields

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('ApplicationTrackingApp')
      .addItem('Refresh form','refreshForm')
      .addItem('Load session','loadSession')
      .addItem('Record session','recordSession')
      .addItem('complete current Step','completeStep')
      .addToUi();
}

function completeStep(){
  // records current time for active step and
  // advances to the next step
  // 01 identify the active steps
  // 01.01 get the active form range
  var formRng = ss.getRangeByName("form_session");
  var Nform = formRng.getNumRows();
  var Mfields = formRng.getNumColumns();
  var stepids = formRng.offset(0,stepOffset,Nform,1).getValues();
  var Nsteps = 0;
  for(i=0;i<Nform;i++){
    if (stepids[i][0]!=""){
      Nsteps = Nsteps + 1;
    }else{
      break;
    }
  }
  if(Nsteps>0){
    var stepRng = formRng.offset(0,0,Nsteps,Mfields);
    // 01.02 get the active step = start has no formula, end has formula
    var isLastStep = true;
    var hasStartFormula = false;
    var hasEndFormula = false;
    for (var i=0;i<Nsteps;i++){
      hasStartFormula = (stepRng.offset(i,startOffset,1,1).getFormula().length>0);
      hasEndFormula = (stepRng.offset(i,startOffset+1,1,1).getFormula().length>0);
      // test for active step condition
      if(!hasStartFormula && hasEndFormula){
        // 02 get current time
        var nowtime = new Date();
        // 03 record the current time into the endtime for the current step
        stepRng.offset(i,startOffset+1,1,1).setValue(nowtime);
        // 04 update the current time to the start of the next step
        //     if not at the last step
        if (i<Nsteps-1){
          stepRng.offset(i+1,startOffset,1,1).setValue(nowtime);
        }else{
          // active step is the last step
        }
        break;
      }
    }
  }else{
    // form empty, no steps
  }
}

function refreshForm(keep_jobid = false) {
  // clears the user input data and refreshes with default values
  // 01 clear the user input values for step id[0], comments[2], start[3] and end[4]
  var formRng = ss.getRangeByName("form_session");
  var Nform = formRng.getNumRows();
  var Nsteps = steps_sht.getLastRow()-1;
  for (var i=0;i<userCol.length;i++){
    formRng.offset(0,userCol[i],Nform,1).clearContent();
  }
  // 02 load default values
  // 02.01 set the sequence of steps in the first column 
  //       of the form to match the ids from 'steps' sheet
  var step_ids = ss.getRangeByName("step_id_hdr").offset(1,0,Nsteps,1).getValues();
  formRng.offset(0,stepOffset,Nsteps,1).setValues(step_ids);  
  // 02.02 initialize the start timestamp for the first step with the current time
  var nowtime = new Date();
  var startEndRng = formRng.offset(0,startOffset,Nsteps,2);
  startEndRng.offset(0,0,1,1).setValue(nowtime);
  // 02.03 load formulas for the end time from step 1 to step N
  fillFormula(ss.getRangeByName("end_formula"),startEndRng.offset(0,1,Nsteps,1));
  // 02.04 load formulas in the start time from step 2 to step N
  fillFormula(ss.getRangeByName("start_formula"),startEndRng.offset(1,0,Nsteps-1,1));
  if(!keep_jobid){
    // 03 clear the jobid field
    ss.getRangeByName("jobid").clearContent();
  }
}

function loadSession() {
  // refreshForm(true)
  // 01 check if session records exist for the jobid
  // 01.01 check if jobid field is empty
  var hasRcds = false;
  var jobid = ss.getRangeByName("jobid").getValue();
  hasRcds = jobid.length>0;
  if (hasRcds){
    // 01.02 check if there are any session records
    var rcdsRng = getRcdsRng();
    var N = rcdsRng.getNumRows()-1;
    var M = rcdsRng.getNumColumns();
    hasRcds = N>0;
    if (hasRcds){
      // 01.03 check if session records exist for the jobid
      var jobidOffset = 0;
      var jobids = rcdsRng.offset(1,jobidOffset,N,1).getValues();
      for(var i=0;i<jobids.length;i++){
        hasRcds = (jobids[i][0]==jobid);
        if(hasRcds){
          break;
        }
      }
      if(hasRcds){
        // 02 get the session records for the jobid 
        var session_all = rcdsRng.offset(1,jobidOffset+1,N,M-1).getValues();
        var session_job = Array();
        var session_step = Array();
        for(var i=0;i<N;i++){
          if(jobids[i][0]==jobid){
            session_step = session_all[i]; 
            session_job.push(session_step)
          }
        }
        // 03 check if the length of records exceeds the form length 
        var formRng = ss.getRangeByName("form_session");
        var Nform = formRng.getNumRows();
        var Nsteps = session_job.length;
        if(Nsteps<=Nform){
          // 04 update the session records in the form for the user-input fields only
          for(var i=0;i<Nsteps;i++){
            for(var j=0;j<userCol.length;j++){
              formRng.offset(i,userCol[j],1,1).setValue(session_job[i][userCol[j]]);
            }          
          }
        }else{
          Browser.msgbox("# of session records for job:"+String(Nsteps)+" exceeds form limit");
        }
      }
    }
  }  
}

function recordSession() {  
  // record session data from 'logsheet' into 'session'
  var IndexColOffset = -1;
  var jobid = ss.getRangeByName("jobid").getValue();
  var form_Values = ss.getRangeByName("form_session").getValues();
  var form_Index = ss.getRangeByName("form_session").offset(
    0,IndexColOffset,form_Values.length,1).getValues();
  
  // build the session activity into an array of values and indexes
  // rcdArray is NxM Array N rows = # session records, M = # fields
  // rcdIndex is Nx1 Array N rows = # session records
  var rcdValues = Array();
  var rcdIndex = Array();
  // loop through each record in the table until reaching the first blank record
  for(var i=0;i<form_Values.length;i++) {
    var rcd = form_Values[i];
    if (rcd[stepOffset]!=""){
      // add the jobid to the front of the rcd record
      rcd.unshift(jobid);
      // add the record and the index
      rcdValues.push(rcd);
      rcdIndex.push(form_Index[i]);
    } else {
      break;
    }
  }
  if(rcdValues.length>0){
      // filters only the new records, drops any duplicates already recorded
    var rcdsRng = getRcdsRng();
    var newRcdArray = newRecords(rcdValues,rcdIndex,rcdsRng,IndexColOffset);
    if (newRcdArray.length>0){
      createRecords(newRcdArray,rcdsRng);
    }
  }  
  // refresh the logsheet form
  refreshForm();
}

function newRecords(rcdValues,rcdIndex,rcdsRng,IndexColOffset){
  var newRcds = Array();
  var Nrcd = rcdValues.length;
  var N = rcdsRng.getNumRows()-1;
  if ((Nrcd>0) && (Nrcd == rcdIndex.length)){
    if(N>0){
      // filter new from existing records
      var destIndexes = rcdsRng.offset(1,IndexColOffset,N,1).getValues();
      for (var i=0;i<Nrcd;i++){
        // check if rcdIndex[i] already exists in destIndexes
        var isNewRcd = true;
        for(var z=0;z<destIndexes.length;z++){
          isNewRcd = (destIndexes[z][0]!=rcdIndex[i]);
          if(!isNewRcd){
            break;
          }
        }
        if(isNewRcd){
          // if not, add the record to newRcds
          newRcds.push(rcdValues[i])
        }
      }
    }else{
      // all are new records
      newRcds = rcdValues
    }
  }
  return newRcds;
}

function createRecords(rcdArray,rcdsRng){
  // stores new records from rcdArray to last rows of destination range
  // WARNING: column dimensions of rcdArray and dest_rng_hdr must match
  // 01 get the number of records to add
  var Nrcd = rcdArray.length;
  if (Nrcd>0){
    var Mrcd = rcdArray[0].length;
    var Mfields = rcdsRng.getNumColumns();
    if (Mrcd==Mfields){
      var N = rcdsRng.getNumRows()-1;
      // 02 get the new rows range
      var NewRows = rcdsRng.offset(N+1,0,Nrcd,Mrcd);
      // 03 write the records into the last rows
      NewRows.setValues(rcdArray);
    } else {
      msgStr = "cannot create record: \n" 
      msgStr = msgStr + "number of columns does not match source and destination"
      Browser.msgBox(msgStr)
    }
  } 
}

function getRcdsRng(){
  var rcd_fieldRngA1 = "B1:B";
  var rcd_hdr = ss.getRangeByName("session_records_hdr");
  var valueColumn = rcd_sht.getRange(rcd_fieldRngA1).getValues();
  var N = valueColumn.filter(String).length;
  var M = rcd_hdr.getNumColumns();
  rcdsRng = rcd_hdr.offset(0,0,N,M);
  return rcdsRng
}

function fillFormula(formRng,destRng){
    formRng.copyTo(destRng,SpreadsheetApp.CopyPasteType.PASTE_FORMULA);
}