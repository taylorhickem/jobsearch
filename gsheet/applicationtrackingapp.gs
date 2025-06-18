var ss = SpreadsheetApp.getActiveSpreadsheet();
var open_sht = ss.getSheetByName("open");
var closed_sht = ss.getSheetByName("closed");
var screened_sht = ss.getSheetByName("screened");
var report_sht = ss.getSheetByName("report");
var kpi_sht = ss.getSheetByName("kpi");
var eval_sht = ss.getSheetByName("evaluated");
var form_sht = ss.getSheetByName("eval_form");
var screened_sht = ss.getSheetByName("screened");
var match_sht = ss.getSheetByName("match");
var config_sht = ss.getSheetByName("config");
var kw_tags_sht = ss.getSheetByName("keyword_tags");

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('JobsearchApp')
      .addItem('Record track assignments','recordTrackAssignments')
      .addItem('Record applications','recordApplications')
      .addItem('Select in process applications','selectApplyInProcess')
      .addItem('Close leads','closeLeads')
      .addToUi();
}

function recordKPIs() {
  var offer_lh = ss.getRangeByName("offer_likelihood").getValue();
  var prospect_val = Math.round(ss.getRangeByName("prospect_value").getValue());
  var kpiRows = [];
  var offer_row = KPIrow("offer_likelihood", offer_lh)
  kpiRows.push(offer_row)
  var offer_row = KPIrow("prospect_value", prospect_val)
  kpiRows.push(offer_row)
  var Nkpi = lastNonEmptyRow(kpi_sht);
  kpi_sht.getRange(Nkpi + 1, 1, kpiRows.length, offer_row.length).setValues(kpiRows);
}

function KPIrow(kpi, value) {
  var row = [];
  row.push(new Date());
  row.push(kpi);
  row.push(value);
  return (row)  
}

function closeLeads() {
  var Napplied = open_sht.getLastRow()-2;
  var Nfields = ss.getRangeByName("open_hdr").getNumColumns();  
  var appliedData = ss.getRangeByName("open_hdr").offset(2,0,Napplied,Nfields).getValues();
  var is_closed = 0;
  var openRows = [];
  var closedRows = [];

  // isolate closed from open leads
  for (var i = 0; i < appliedData.length; i++) {
      is_closed = appliedData[i][Nfields-1]
      if (is_closed == 1) {
        // close lead
        var closedRow = appliedData[i].slice(0, Nfields-1); // Get data fields
        closedRow.push(new Date()); // Add current timestamp
        closedRows.push(closedRow);
      } else if (is_closed == 0) {
        // Row to keep
        openRows.push(appliedData[i].slice(0, Nfields-2));
    }
  }  

  // Append rows to the "closed" sheet
  var Nclosed = lastNonEmptyRow(closed_sht);
  if (closedRows.length > 0) {
    closed_sht.getRange(Nclosed + 1, 1, closedRows.length, Nfields).setValues(closedRows);
  }  

  // Clear and update the "open" sheet
  ss.getRangeByName("open_hdr").offset(2, 0, Napplied, Nfields).clearContent();
  if (openRows.length > 0) {
    ss.getRangeByName("open_hdr").offset(2, 0, openRows.length, Nfields-2).setValues(openRows);
  }
}

function recordApplications() {

  // update selections with application results
  selectApplySuccess()
  // clear jobs that are no longer in-process
  clearApplyInProcess()

  var Napplyfields = 13
  var Nscreened = screened_sht.getLastRow()-1;
  var Nscreenfields = ss.getRangeByName("screened_data_hdr").getNumColumns();  
  var screenedData = ss.getRangeByName("screened_data_hdr").offset(1,0,Nscreened,Nscreenfields).getValues();
  var to_apply = ss.getRangeByName("to_apply_hdr").offset(1,0,Nscreened,1).getValues();
  var applyRows = [];

  // isolate leads to apply from screened
  for (var i = 0; i < screenedData.length; i++) {
      if (to_apply[i][0] == 1) {
        // apply lead
        var screenedRow = screenedData[i]
        var applyRow = [];

        applyRow.push(screenedRow[2]) //               01 jobid 
        applyRow.push(screenedRow[3]) //               02 url
        applyRow.push(screenedRow[0]) //               03 title
        applyRow.push(screenedRow[1]) //               04 company
        applyRow.push('') //                           05 lead source
        applyRow.push('') //                           06 apply method
        applyRow.push(screenedRow[9]) //               07 deadline
        applyRow.push(new Date()) //                   08 applied
        applyRow.push('') //                           09 1st attempt
        applyRow.push('') //                           10 last contact
        applyRow.push('') //                           11 notes
        applyRow.push('') //                           12 job profile
        applyRow.push('pending callback') //           13 status

        applyRows.push(applyRow);
        ss.getRangeByName("to_apply_hdr").offset(i + 1, 0, 1, 1).clearContent();
    }
  }  

  // Append rows to the "open"
  var Nopen = lastNonEmptyRow(open_sht);
  if (applyRows.length > 0) {
    open_sht.getRange(Nopen + 1, 1, applyRows.length, Napplyfields).setValues(applyRows);
  }  

}


function drawJobs() {
  // draw N unevaluated jobids from screened 
  // and post to sheet 'match' as a shortlist for evaluation
  // 1) get N = jobid_samples_n from 'config'
  var Njobs_max = ss.getRangeByName("jobid_samples_n").getValue();
  var alpha = ss.getRangeByName("jobid_samples_alpha").getValue();
  var match_jidRng = ss.getRangeByName("match_jobid_hdr").offset(1,0,Njobs_max,1);
  // 2) get list of jobids from 'evaluated'
  var Neval = eval_sht.getLastRow()-1;
  var eval = getColumn(ss.getRangeByName("evaluated_jobid_hdr").offset(1,0,Neval,1).getValues(),0);
  // 3) get list of jobids from 'screened'
  var Nscreened = screened_sht.getLastRow()-1;
  var screened = getColumn(ss.getRangeByName("screened_jobid_hdr").offset(1,0,Nscreened,1).getValues(),0);
  // 4) in order, loop through the screened jobids, skipping those
  //  which are in 'evaluated'. 
  var Nuneval_max = alpha*Njobs_max;
  var Nuneval = Nuneval_max;
  var uneval = Array();
  // Set the length of uneval to the smaller of alpha*N or # of screened jobs
  if (Nscreened < Nuneval){
    Nuneval = Nscreened;
  }
  var jobid = screened[0];
  for(var i=0;i<Nuneval;i++){
    // check if jobid already evaluated
    jobid = screened[i];
    if (eval.indexOf(jobid) == -1){
      // if unevaluated, add to list
      uneval.push([jobid])
    }
  }
    
  // 5) draw N random samples from the shortlist, if the shortlist is shorter than Njobs,
  //     then reduce Njobs to match the shortlist. If there are no jobids left then exit
  Nuneval = uneval.length;  
  if(Nuneval>0){
    var Njobs = Njobs_max;
    if(Nuneval < Njobs){
      Njobs = Nuneval;
    }
    var jobSamples = Array();
    var jobid_sample = 0;
    for (var i=0;i<Njobs;i++){
      jobid_sample = Math.round(Math.random()*Nuneval,1);
      jobSamples.push([uneval[0,jobid_sample]]);
      uneval.splice(jobid_sample,1);
      Nuneval = uneval.length;
    }
    // 6) post the drawn jobid samples to 'match'
    match_jidRng.clearContent();
    match_jidRng = ss.getRangeByName("match_jobid_hdr").offset(1,0,Njobs,1);  
    match_jidRng.setValues(jobSamples);
    // Browser.msgBox('posted ' +String(Njobs)+ ' new jobs to evaluate');
  }
    else{
      Browser.msgBox('No unevaluated jobids found in sheet "screened"');
  }
}


function get_last_row(rng) {
  var i = 0;
  while ( rng.offset(i, 0).getValue() != "" ) {
    i++;
  }
  return (i);
}


function recordEvaluation() {
  // creates an evaluation record from 'eval_form' 
  // and adds a new row to 'evaluated'
  // 1) get 3 range sections - jobid, scores, keywords
  var jobid = ss.getRangeByName("form_jobid").getValues();
  var scores = ss.getRangeByName("form_scores").getValues();
  var formal_tbl = ss.getRangeByName("form_formal").getValues();
  var keyword_tbl = ss.getRangeByName("form_keywords").getValues();
  
  // 2) get the new row range in evaluated
  var Neval = get_last_row(ss.getRangeByName("evaluated_timestamp"))-1;
  var Meval = ss.getRangeByName("evaluated_hdr").getNumColumns();
  var evalNewRow = ss.getRangeByName("evaluated_hdr").offset(Neval+1,0,1,Meval)
   
  // 3) create the new record
  var rcd = Array(16);
  var nowtime = new Date();
  
  rcd[0] = nowtime;      // 01 date	
  rcd[1] = jobid[0][0];  // 02 jobid	
  rcd[2] = jobid[1][0];  // 03 short title	
  rcd[3] = scores[0][0]; // 04 match_eval	
  rcd[4] = scores[1][0]; // 05 match_man	
  rcd[5] = scores[2][0]; // 06 match_mcf	
  rcd[6] = scores[3][0]; // 07 match_formal
  rcd[7] = scores[4][0]; // 08 match_keyword	
  rcd[8] = scores[5][0]; // 09 keyword_count_match	
  rcd[9] = scores[6][0]; // 10 keyword_count_some	
  rcd[10] = scores[7][0]; // 11 keyword_count_no_match	
  rcd[11] = scores[8][0]; // 12 formal_level
  
  // construct the formal qualification keyword strings
  var kwFormalStr = '';
  if (formal_tbl.length>0){
    for(var i=0;i<keyword_tbl.length;i++){
      if (formal_tbl[i][0]!=''){
        if (kwFormalStr==''){
          kwFormalStr = formal_tbl[i][0];
        }else{
          kwFormalStr = kwFormalStr + ', ' + formal_tbl[i][0];
        }
      } else {
        break;
      }
    }
  }
  rcd[12] = kwFormalStr; // 13 keywords_formal	
  
  // construct the keyword strings for match, some, and none
  var kwMatchStr = '';
  var kwSomeStr = '';
  var kwNoneStr = '';
  var score = 0;
  if (keyword_tbl.length>0){
    for(var i=0;i<keyword_tbl.length;i++){ 
      if (keyword_tbl[i][0]!=''){
        score = keyword_tbl[i][2];
        switch (score){
          case 1: // match
            if (kwMatchStr==''){
              kwMatchStr = keyword_tbl[i][0];
              break;
            }else{
              kwMatchStr = kwMatchStr + ', ' + keyword_tbl[i][0];
              break;
            }
            break;
          case -1: // none
            if (kwNoneStr==''){
              kwNoneStr = keyword_tbl[i][0];
              break;
            }else{
              kwNoneStr = kwNoneStr + ', ' + keyword_tbl[i][0];
              break;
            }
            break;
          default: // some
            if (kwSomeStr==''){
              kwSomeStr = keyword_tbl[i][0];
            }else{
              kwSomeStr = kwSomeStr + ', ' + keyword_tbl[i][0];
            }
        }
        
      } else {
        break;
      }
    }
  }
  rcd[13] = kwMatchStr; // 14 keywords_match	
  rcd[14] = kwSomeStr; // 15 keywords_some	
  rcd[15] = kwNoneStr; // 16 keywords_no_match

  // 4) write record into the new row
  evalNewRow.setValues([rcd]);

  // 5) update keyword library
  updateKeywordLib();

  // 6) clear contents and reset view back to 'eval_form'
  ss.getRangeByName("form_jobid").offset(1,0,1,1).clearContent();
  ss.getRangeByName("form_keywords").clearContent();
  ss.getRangeByName("form_formal").clearContent();
}

function updateKeywordLib() {
  // update 'keyword_tags' with new keywords
  // 1) load the keyword table
  var Nkw = ss.getRangeByName("form_keywords").getNumRows();
  var kw_tbl = ss.getRangeByName("form_keywords").offset(0,0,Nkw,5).getValues();
  // 2) construct the non-matching keyword table based on #NA
  var isNew = false;
  var Mfld = 3; // # keyword tag columns
  var lookupCol = 3;
  var kw_tbl_new = Array();
  if (kw_tbl.length>1){
    for(var i=1;i<kw_tbl.length;i++){
      if (kw_tbl[i][lookupCol]=='#N/A'){
        var rcd = Array(3);
        rcd[0] = kw_tbl[i][1]; // group
        rcd[1] = kw_tbl[i][0]; // keyword
        rcd[2] = kw_tbl[i][2]; // score
        kw_tbl_new.push(rcd);
      }
    } 
  }  
  if (kw_tbl_new.length>0){
    // 3) get the new row starting position in 'keyword_tags'
    // 4) write the new keywords into the new rows
    var Ntgs = kw_tags_sht.getLastRow()-1;
    var tgNewRows = ss.getRangeByName("keyword_tags_hdr").offset(Ntgs+1,0,kw_tbl_new.length,Mfld)
    tgNewRows.setValues(kw_tbl_new);
  }
}


function recordTrackAssignments() {
  const srcSheet = ss.getSheetByName("track_un");
  const dstSheet = ss.getSheetByName("track_assignment");

  const srcRange = srcSheet.getRange("A2:B" + srcSheet.getLastRow());
  const srcValues = srcRange.getValues();

  const toAppend = [];

  for (let i = 0; i < srcValues.length; i++) {
    const jobid = srcValues[i][0];
    const track_id = srcValues[i][1];

    // Skip rows with blank track_id
    if (track_id !== "") {
      toAppend.push([jobid, track_id]);
    }
  }
  if (toAppend.length > 0) {
    const dstLastRow = lastNonEmptyRow(dstSheet);
    dstSheet.getRange("A1").offset(dstLastRow, 0, toAppend.length, 2).setValues(toAppend);

    // clear assignments from source
    srcRange.offset(0,1,toAppend.length,1).clearContent()
  } 
}

function selectApplySuccess() {
  const applySheet = ss.getSheetByName("apply_results");
  const screened = ss.getSheetByName("screened");

  // Step 1: Collect jobids with apply_status = 1 from apply_results
  const resultsData = applySheet.getRange("A2:B" + lastNonEmptyRow(applySheet)).getValues();
  const jobidsSuccess = new Set();

  resultsData.forEach(row => {
    const jobid = row[0];
    const apply_status = row[1];
    if (apply_status === 1) {
      jobidsSuccess.add(jobid);
    }
  });

  Logger.log(`Identified ${jobidsSuccess.size} jobid(s) with apply_status = 1`);
  // Logger.log([...jobidsSuccess].join("\n"));

  // Step 2: Update apply (col R) in screened
  const screenedRange = screened.getRange("E2:R" + lastNonEmptyRow(screened));
  const screenedData = screenedRange.getValues();

  for (let i = 0; i < screenedData.length; i++) {
    const jobid = screenedData[i][0];   // Col E
    const shouldApply = jobidsSuccess.has(jobid);
    screenedData[i][13] = shouldApply ? 1 : "";  // Col R = index 13
  }

  // Write back the updated apply column (col R)
  const applyUpdateRange = screened.getRange("R2:R" + (screenedData.length + 1));
  const updatedApplyColumn = screenedData.map(row => [row[13]]);
  applyUpdateRange.setValues(updatedApplyColumn);
}

function clearApplyInProcess() {
  const screened = ss.getSheetByName("screened");
  const applySheet = ss.getSheetByName("apply_results");

  // Step 1: Build a set of jobids to KEEP from screened
  const screenedData = screened.getRange("E2:W" + lastNonEmptyRow(screened)).getValues();
  const jobidsToKeep = new Set();

  screenedData.forEach(row => {
    const jobid = row[0];        // Column E (jobid)
    const apply = row[13];       // Column R (apply)
    const closed = row[18];      // Column W (closed)

    if (apply !== 1 && closed === 0) {
      jobidsToKeep.add(jobid);
    }
  });

  Logger.log(`found ${jobidsToKeep.size} jobids to keep from screened`);

  // Step 2: Filter apply_results for only those jobids
  const dataRange = applySheet.getRange("A2:D" + lastNonEmptyRow(applySheet));
  const data = dataRange.getValues();
  const retainedRows = data.filter(row => jobidsToKeep.has(row[0]));

  Logger.log(`keep in process rows:`);
  Logger.log(retainedRows);

  // Step 3: Clear and rewrite
  dataRange.clearContent();

  if (retainedRows.length > 0) {
    applySheet.getRange("A2").offset(0, 0, retainedRows.length, 4).setValues(retainedRows);
    Logger.log(`apply_results updated with ${retainedRows.length} retained rows.`);
  } else {
    Logger.log("apply_results fully cleared (no retained rows).");
  }
}

function selectApplyInProcess() {
  const applySheet = ss.getSheetByName("apply_results");
  const screenedSheet = ss.getSheetByName("screened");

  // Step 1: Collect jobids with applied = 0 (i.e., failed)
  const resultsJobids = applySheet.getRange("A2:A" + lastNonEmptyRow(applySheet)).getValues();
  const jobidList = resultsJobids.map(row => row[0]); 
  const jobidInProcess = new Set(jobidList);

  Logger.log(`Found ${jobidInProcess.size} job(s) to select`);
  Logger.log([...jobidInProcess].join("\n"));

  // Step 2: Update "apply" column in screened sheet
  const screenedRange = screenedSheet.getRange("E2:R" + lastNonEmptyRow(screenedSheet));
  const screenedData = screenedRange.getValues();

    for (let i = 0; i < screenedData.length; i++) {
      const jobid = screenedData[i][0];  // column E
      if (jobidInProcess.has(jobid)) {
        screenedData[i][13] = 1;  // column R (index 13) = apply
    }
  }

  // Step 3: Write updated "apply" column (R)
  const applyColRange = screenedSheet.getRange("R2:R" + (screenedData.length + 1));
  const updatedApplyColumn = screenedData.map(row => [row[13]]);
  applyColRange.setValues(updatedApplyColumn);
}


function getColumn(array2D,col_index){
  // selects column i and returns as a 1D array (list)
  var array1D = Array();
  if (array2D.length>0){
    for(var i=0;i<array2D.length;i++){
      array1D.push(array2D[i][col_index])
    }
  }
  return array1D
}

function lastNonEmptyRow(sheet) {
  var data = sheet.getDataRange().getValues();
  for (var i = data.length - 1; i >= 0; i--) {
    if (data[i][0] !== '') {
      return i + 1;
    }
  }
  return 0; // Sheet is empty
}