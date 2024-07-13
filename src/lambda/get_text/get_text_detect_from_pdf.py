import json
import pandas as pd
import awswrangler as wr
import boto3
import os

textract = boto3.client('textract')
s3 = boto3.client('s3')

output_bucket = os.environ["OUT_PUT_S3_BUCKET"]
glue_catalog_db_name = os.environ['GLUE_CATALOG_DB_NAME']
glue_catalog_table_name = os.environ['GLUE_CATALOG_TABLE_NAME']

def handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    jobId = message['JobId']
    docName = str(message['DocumentLocation']['S3ObjectName']).replace('.pdf','')
    print("JobId="+jobId)
    

    status = message['Status']
    print("Status="+status)

    if status != "SUCCEEDED":
        return {
            # TODO : handle error with Dead letter queue (not in this workshop)
            # https://docs.aws.amazon.com/lambda/latest/dg/dlq.html
            "status": status
        }
    
    text_extractor = TextExtractor()
    pages = text_extractor.extract_text(jobId, docName)
    file = docName + '_' + jobId

    df = pd.DataFrame(list(pages.values()))

    wr_response = wr.s3.to_parquet(
        df=df,
        path=f's3://{output_bucket}/{file}.snappy.parquet',
        dataset=False
    )

    #content = json.dumps(list(pages.values()), indent=4, separators=(", ", ": "), ensure_ascii=False)
    #f = open("/tmp/file.txt", "w")
    #f.write(content)
    #f.close()
    #s3_response = s3.upload_file("/tmp/file.txt",output_bucket,file+".txt")

    return wr_response

class TextExtractor():
    def extract_text(self, jobId, docName):
        """ Extract text from document corresponding to jobId and
        generate a list of pages containing the text
        """

        textract_result = self.__get_textract_result(jobId)
        pages = {}
        self.__extract_all_pages(jobId, textract_result, pages, [], docName)
        return pages

    def __get_textract_result(self, jobId):
        """ retrieve textract result with job Id """

        result = textract.get_document_text_detection(
            JobId=jobId
        )

        return result

    def __extract_all_pages(self, jobId, textract_result, pages, page_numbers, docName):
        """ extract page content: build the pages array,
        recurse if response is too big (when NextToken is provided by textract)
        """

        blocks = [x for x in textract_result['Blocks']
                  if x['BlockType'] == "LINE"]
        for block in blocks:
            if block['Page'] not in page_numbers:
                page_numbers.append(block['Page'])
                pages[block['Page']] = {
                    "Document": docName + '.pdf',
                    "Page": block['Page'],
                    "Content": block['Text']
                }
            else:
                pages[block['Page']]['Content'] += " " + block['Text']

        nextToken = textract_result.get("NextToken", "")
        if nextToken != '':
            textract_result = textract.get_document_text_detection(
                JobId=jobId,
                NextToken=nextToken
            )
            self.__extract_all_pages(jobId,
                                     textract_result,
                                     pages,
                                     page_numbers,
                                     docName)