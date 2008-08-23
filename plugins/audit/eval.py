'''
eval.py

Copyright 2008 Viktor Gazdag & Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import core.data.kb.vuln as vuln
from core.data.fuzzer.fuzzer import createMutants
from core.data.fuzzer.fuzzer import createRandAlpha
import core.controllers.outputManager as om

# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.basePlugin.baseAuditPlugin import baseAuditPlugin

import core.data.kb.knowledgeBase as kb
from core.controllers.w3afException import w3afException
import core.data.parsers.urlParser as urlParser
import core.data.constants.severity as severity
import re

#Create some random strings, which the plugin will use.
Rndn1 = createRandAlpha(5)
Rndn2 = createRandAlpha(5)
Rndn = Rndn1 + Rndn2

class eval(baseAuditPlugin):
    '''
    Finds incorrect usage of the eval().

    @author: Viktor Gazdag ( woodspeed@gmail.com ) & Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseAuditPlugin.__init__(self)
        
    def _fuzzRequests(self, freq ):
        '''
        Tests an URL for eval() user input injection vulnerabilities.

        @param freq: A fuzzableRequest
        '''
        om.out.debug( 'eval plugin is testing: ' + freq.getURL() )

        oResponse = self._sendMutant( freq , analyze=False ).getBody()
        evalStrings = self._getEvalStrings()
        mutants = createMutants( freq , evalStrings, oResponse=oResponse )

        for mutant in mutants:
            if self._hasNoBug( 'eval' , 'eval' , mutant.getURL() , mutant.getVar() ):
                # Only spawn a thread if the mutant has a modified variable
                # that has no reported bugs in the kb
                targs = (mutant,)
                self._tm.startFunction( target=self._sendMutant, args=targs, ownerObj=self )

    def _getEvalStrings( self ):
        '''
        Gets a list of strings to test against the web app.
        @return: A list with all the strings to test.
        '''
        Evalstr = []
        # PHP
        Evalstr.append("echo \x27"+ Rndn1 +"\x27 . \x27"+ Rndn2 +"\x27;")
        # ASP
        Evalstr.append("Response.Write\x28\x22"+Rndn1+"+"+Rndn2+"\x22\x29")
        return Evalstr

    def _analyzeResult( self, mutant, response ):
        '''
        Analyze results of the _sendMutant method.
        '''

        EvalErrorList = self._findEvalError( response )
        for evalError in EvalErrorList:
            if not re.search( evalError, mutant.getOriginalResponseBody(), re.IGNORECASE ):
                v = vuln.vuln( mutant )
                v.setId( response.id )
                v.setSeverity(severity.HIGH)
                v.setName( 'eval() input injection vulnerability' )
                v.setDesc( 'eval() input injection was found at: ' + mutant.foundAt() )
                kb.kb.append( self, 'eval', v )      
    
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self._tm.join( self )
        self.printUniq( kb.kb.getData( 'eval', 'eval' ), 'VAR' )

    def _findEvalError( self, response ):
        '''
        This method searches for the randomized Rndn string in html's.
        
        @parameter response: The HTTP response object
        @return: A list of error found on the page
        '''
        res = []
        for evalError in self._getEvalErrors():
            match = re.search( evalError, response.getBody() , re.IGNORECASE )
            if match:
                msg = 'Verified eval() input injection, found the concatenated random string: "' + response.getBody()[match.start():match.end()] + '" '
                msg += 'in the response body. '
                msg += 'The vulnerability was found on response with id ' + str(response.id) + '.'
                om.out.debug( msg )
                res.append( evalError )
        return res
        
    def _getEvalErrors( self ):
        errorStr = []
        errorStr.append( Rndn )
        return errorStr

    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''    
        ol = optionList()
        return ol

    def setOptions( self, OptionList ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        pass

    def getPluginDeps( self ):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return []
    
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin finds eval() input injection vulnerabilities. These vulnerabilities are found in web applications, when the developer
        passes user controled data to the eval() function. To check for vulnerabilities of this kind, the plugin sends an echo function
        with two randomized strings as a parameters (echo 'abc' + 'xyz') and if the resulting HTML matches the string that corresponds
        to the evaluation of the expression ('abcxyz') then a vulnerability has been found.
        '''
