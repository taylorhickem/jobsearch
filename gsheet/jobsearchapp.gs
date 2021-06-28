// project: jobsearchApp
var ss = SpreadsheetApp.getActiveSpreadsheet();
var eval_sht = ss.getSheetByName("evaluated");
var form_sht = ss.getSheetByName("eval_form");
var screened_sht = ss.getSheetByName("screened");
var match_sht = ss.getSheetByName("match");
var config_sht = ss.getSheetByName("config");
var kw_tags_sht = ss.getSheetByName("keyword_tags");

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('JobsearchApp')
      .addItem('Draw jobs','drawJobs')
      .addItem('Record evaluation','recordEvaluation')
      .addItem('Update keyword library','updateKeywordLib')
      .addToUi();
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

function recordEvaluation() {
  // creates an evaluation record from 'eval_form'
  // and adds a new row to 'evaluated'
  // 1) get 3 range sections - jobid, scores, keywords
  var jobid = ss.getRangeByName("form_jobid").getValues();
  var scores = ss.getRangeByName("form_scores").getValues();
  var formal_tbl = ss.getRangeByName("form_formal").getValues();
  var keyword_tbl = ss.getRangeByName("form_keywords").getValues();

  // 2) get the new row range in evaluated
  var Neval = eval_sht.getLastRow()-1;
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